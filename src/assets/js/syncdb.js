let username = '';  // required, do not delete
let syncURL = '';
let batchSize = 10000;
let liveInterval = 60;  //seconds
let wsEndpointUrl = '';
let jwtAccessToken = '';
let jwtRefreshToken = '';  // required, do not delete

let dbPromise = null;

const LOADED_QUERY_ENTRY = '代码库';  // const LOADED_QUERY_ENTRY = '写进';
const EXPORTS_LIST_PATH = '/enrich/exports.json';

import {
  SubscriptionClient
} from 'subscriptions-transport-ws';

import {
  addRxPlugin,
  createRxDatabase,
  removeRxDatabase,
} from 'rxdb/plugins/core';

addRxPlugin(require('pouchdb-adapter-idb'));
import {
  RxDBReplicationGraphQLPlugin,
  pullQueryBuilderFromRxSchema,
  pushQueryBuilderFromRxSchema,
} from 'rxdb/plugins/replication-graphql';
addRxPlugin(RxDBReplicationGraphQLPlugin);

// TODO import these only in non-production build
// import { RxDBDevModePlugin } from 'rxdb/plugins/dev-mode';
// addRxPlugin(RxDBDevModePlugin);

// FIXME: only validate in dev and for not web extension (has `eval`)
// import { RxDBValidatePlugin } from 'rxdb/plugins/validate';
// addRxPlugin(RxDBValidatePlugin);
import { RxDBNoValidatePlugin } from 'rxdb/plugins/no-validate';
addRxPlugin(RxDBNoValidatePlugin);

import { RxDBMigrationPlugin } from 'rxdb/plugins/migration';
addRxPlugin(RxDBMigrationPlugin);
import { RxDBUpdatePlugin } from 'rxdb/plugins/update';
addRxPlugin(RxDBUpdatePlugin);

import { RxDBQueryBuilderPlugin } from 'rxdb/plugins/query-builder';
addRxPlugin(RxDBQueryBuilderPlugin);

import { getFileStorage } from './idb-file-storage.js';

import {
  wordId,
  cardType,
  CARD_SCHEMA,
  WORD_SCHEMA,
  WORD_LIST_SCHEMA,
  WORD_MODEL_STATS_SCHEMA,
  graphQLGenerationInput,
  EVENT_QUEUE_SCHEMA,
  CONTENT_CONFIG_SCHEMA,
} from './schemas';

import { addAuthHeader, fetchWithNewToken, parseJwt } from './lib.js';

const WORD_MODEL_STATS_CHANGED_QUERY = `
  subscription onChangedWordModelStats($token: String!) {
    changedWordModelStats(token: $token) {
      dummy
    }
  }
`;

const WORD_LIST_CHANGED_QUERY = `
  subscription onChangedWordList($token: String!) {
    changedWordList(token: $token) {
      dummy
    }
  }
`;

const DEFINITION_CHANGED_QUERY = `
  subscription onChangedDefinition($token: String!) {
    changedDefinition(token: $token) {
      dummy
    }
  }
`;

const CARD_CHANGED_QUERY = `
  subscription onChangedCard($token: String!) {
    changedCard(token: $token) {
      cardId
    }
  }
`;

const pullDefsQueryBuilder = doc => {
  if (!doc) {
    // the first pull does not have a start-document
    doc = {
      wordId: '',
      updatedAt: 0
    };
  }
  const query = `{
    feedDefinitions(wordId: "${doc.wordId}", updatedAt: ${doc.updatedAt}, limit: ${batchSize}) {
      frequency {
        pos
        posFreq
        wcdp
        wcpm
      }
      graph
      hsk { levels }
      wordId
      providerTranslations {
        posTranslations {
          posTag
          values
        }
        provider
      }
      synonyms {
        posTag
        values
      }
      sound
      updatedAt
      deleted
    }
  }`;
  return {
    query,
    variables: {}
  };
};

const pullWordModelStatsQueryBuilder = pullQueryBuilderFromRxSchema(
  'wordModelStats',
  graphQLGenerationInput.wordModelStats,
  batchSize
);

const pullWordListQueryBuilder = pullQueryBuilderFromRxSchema(
  'wordList',
  graphQLGenerationInput.wordList,
  batchSize
);

const pullQueryBuilder = pullQueryBuilderFromRxSchema(
  'card',
  graphQLGenerationInput.card,
  batchSize
);

const pushQueryBuilder = pushQueryBuilderFromRxSchema(
  'card',
  graphQLGenerationInput.card
);

/**
 * should this be configurable?
 */
function getDatabaseName(config) {
  if (config.test) {
    return 'tmploadtest';
  } else {
    const baseName = 'tc-' + config.username + "-" + (new URL(config.syncURL)).hostname;
    return baseName.toLowerCase().replace(/[^\w\s]/g,'_');
  }
}

async function deleteDatabase(dbName) {
  if (!!dbPromise) {
    console.log(`Delete existing database by object for ${dbName}...`);
    await (await dbPromise).remove();
  } else {
    console.log(`Delete existing database by name ${dbName}...`);
    await removeRxDatabase(dbName, 'idb');
  }
}

async function createDatabase(dbName) {
  console.log(`Create new database ${dbName}...`);
  return await createRxDatabase({
    name: dbName,
    adapter: 'idb'
  });
}

async function createCollections(db) {
  console.log('Create collections...');
  await db.addCollections({
    cards: {
      schema: CARD_SCHEMA,
      methods: {
        wordId: function () { return wordId(this) },
        cardType: function () { return cardType(this) },
      },
      migrationStrategies: {
        1: function (oldDoc) { return oldDoc; },
        2: function (oldDoc) { return oldDoc; },
        3: function (oldDoc) { return oldDoc; },
      }
    },
    definitions: { schema: WORD_SCHEMA },
    event_queue: { schema: EVENT_QUEUE_SCHEMA },
    content_config: { schema: CONTENT_CONFIG_SCHEMA },
    word_model_stats: {
      schema: WORD_MODEL_STATS_SCHEMA,
      // migrationStrategies: {
      //   1: function (oldDoc) { return oldDoc; },
      // },
    },
    word_lists: {
      schema: WORD_LIST_SCHEMA,
      // migrationStrategies: {
      //   1: function (oldDoc) { return oldDoc; },
      // },
    },
  });
  // add Hooks ???
  // db.cards.preInsert(function(plainData){ }, true);

  // FIXME: the following  is no longer true, now that we are not loading a unified dump but
  // importing from multiple sources
  return ((await db.definitions.findByIds(["670"])).size == 0)  // look for "de", if exists, we aren't new
}

function refreshTokenIfRequired(replicationState, e) {
  try {
    // this is currently a string, but could be made to be json, meaning an elegant parse of the error. But I suck...
    const expiredMessage = e.innerErrors[0].message;
    if (expiredMessage.includes("'token_type': ErrorDetail(string='access', code='token_not_valid')")) {
      console.log('Looks like the token has expired, trying to refresh');
      fetchWithNewToken().then((tokens) => {
        console.debug('The newly refreshed tokens set to the replicationState', tokens);
        replicationState.setHeaders(getHeaders(tokens.accessToken));
      });
    } else {
      console.log('There was an error but apparently not an expiration');
    }
  } catch (error) {
    console.error(error);
    throw error
  }
}

async function testQueries(db) {
  // This makes sure indexes are loaded into memory. After this everything on definitions
  // will be super fast!
  return await db.definitions.find().where('graph').eq(LOADED_QUERY_ENTRY).exec();
}

function setupPullOnlyReplication(collection, queryBuilder) {
  // set up replication
  console.debug('Start pullonly replication');
  const headers = getHeaders(jwtAccessToken);
  const replicationState = collection.syncGraphQL({
    url: syncURL,
    headers: headers,
    pull: {
      queryBuilder: queryBuilder
    },
    live: true,
    liveInterval: 1000 * liveInterval, // liveInterval is in ms, so seconds * 1000
    deletedFlag: 'deleted'
  });
  // show replication-errors in logs
  console.debug('Subscribe to errors for ', queryBuilder);
  replicationState.error$.subscribe(err => {
    console.error('replication error:');
    console.dir(err);
    console.log('Attempting to refresh token for pullonly, if that was the issue');
    refreshTokenIfRequired(replicationState, err);
  });
  return replicationState;
}

function getHeaders(laccessToken){
  const headers = { Authorization: 'Bearer ' + laccessToken };
  if (typeof csrftoken !== 'undefined') {
    headers["X-CSRFToken"] = csrftoken
  }
  return headers;
}

function setupCardsReplication(db) {
  // set up replication
  console.debug('Start cards replication');
  const headers = getHeaders(jwtAccessToken);
  const replicationState = db.cards.syncGraphQL({
    url: syncURL,
    headers: headers,
    push: {
      queryBuilder: pushQueryBuilder,
      batchSize: 10,  // FIXME: this doesn't appear to do anything
    },
    pull: {
      queryBuilder: pullQueryBuilder
    },
    live: true,
    /**
     * Because the websocket is used to inform the client
     * when something has changed,
     * we can set the liveIntervall to a high value
     */
    liveInterval: 1000 * liveInterval, // liveInterval seconds * 1000
    deletedFlag: 'deleted'
  });
  // show replication-errors in logs
  console.debug('Subscribe to cards errors');
  replicationState.error$.subscribe(err => {
    console.error('replication cards error:');
    console.dir(err);
    console.log('Attempting to refresh token cards replication, if that was the issue');
    refreshTokenIfRequired(replicationState, err);
  });
  // replicationState.change$.subscribe(change => {console.log("I just replicated something") && console.dir(change)});
  return replicationState;
}

function setupGraphQLSubscription(replicationState, query) {
  // setup graphql-subscriptions for pull-trigger
  console.debug(`Create SubscriptionClient to endpoint ${wsEndpointUrl}`);

  const wsClient = new SubscriptionClient(
    wsEndpointUrl,
    {
      reconnect: true,
      timeout: 1000 * 60,
      onConnect: () => {
        console.debug('SubscriptionClient.onConnect()');
      },
      connectionCallback: () => {
        console.debug('SubscriptionClient.connectionCallback:');
      },
      reconnectionAttempts: 10000,
      inactivityTimeout: 10 * 1000,
      lazy: true
    });

  console.debug('Subscribe to GraphQL Subscriptions');
  const ret = wsClient.request(
    {
      query,
      /**
       * there is no method in javascript to set custom auth headers
       * at websockets. So we send the auth header directly as variable
       * @link https://stackoverflow.com/a/4361358/3443137
       */
      variables: {
        token: jwtAccessToken
      }
    }
  );
  ret.subscribe({
    next: async (data) => {
      console.log('subscription emitted => trigger run()');
      console.dir(data);
      if (!!data.errors && data.errors.length > 0) {
        console.error(data.errors);
      }
      await replicationState.run();
      console.log('run() done');
    },
    error(error) {
      console.log('run() got error:');
      console.error(error);
    }
  });
}

async function cacheExports(initialisationCache, progressCallback) {
  let fetchInfo = {
    method: "GET",
    cache: "no-store",
    headers: { "Accept": "application/json", "Content-Type": "application/json" },
  };
  // FIXME: this is just plain nasty, I need a proper config manager!!!
  const baseUrl = new URL(syncURL).origin;
  const exportFilesListURL = new URL(EXPORTS_LIST_PATH, baseUrl);
  console.debug(`Going to try and query ${exportFilesListURL} for the list of urls`)
  fetchInfo = addAuthHeader(fetchInfo);
  const data = await fetch(exportFilesListURL, fetchInfo).then(res => {
    if (res.ok) { return res.json(); } throw new Error(res.status);
  }).catch((message) => {
    progressCallback("There was an error downloading the data file. Please try again in a few minutes and if you get this message again, contact Transcrobes support: ERROR!", false);
    console.error(message)
  });

  console.debug('Trying to precache the urls:', data)
  const definitionBlock = async (url, origin)=> {
    const response = await fetch(new URL(url, origin), fetchInfo).then((res) => {
        if (res.ok) { return res.json(); } throw new Error(res.status);
      })
    return await initialisationCache.put(url, new Blob([JSON.stringify(response)], {type : 'application/json'}));
  }
  const allBlocks = await Promise.all(data.map(x => definitionBlock(x, baseUrl)));
  console.debug("Promise.all result from download and caching of all file blocks", allBlocks);
  return await initialisationCache.list();
}

async function loadFromExports(config, progressCallback) {
  const { activateSubscription, reinitialise } = config;
  const initialisationCacheName = `${config.cacheName}.initialisation`;
  const dbName = getDatabaseName(config);
  progressCallback(`Setting up db ${dbName} : 0% complete`, false);
  if (reinitialise) {
    await deleteDatabase(dbName);
  }
  const db = await createDatabase(dbName);
  const justCreated = await createCollections(db);
  progressCallback("Structure created, fetching the data from the server : 3% complete", false);
  if (justCreated || reinitialise) {
    let fetchInfo = {
      method: "GET",
      cache: "no-store",
      headers: { "Accept": "application/json", "Content-Type": "application/json" },
    };
    fetchInfo = addAuthHeader(fetchInfo);

    const initialisationCache = await getFileStorage({name: initialisationCacheName});
    if (reinitialise && await (await initialisationCache.list()).length > 0) {
      console.debug('The initialisation cache existing and we want to reinitialise, deleting')
      await initialisationCache.clear();
    }
    let cacheFiles;
    const existingKeys = await initialisationCache.list();
    console.debug('Found the following existing items in the cache', existingKeys);
    if (justCreated && !reinitialise && existingKeys.length > 0) {
      // we have unsuccessfully started an initialisation, and want to continue from where we left off
      console.debug('Using the existing keys of the cache because', justCreated, reinitialise, existingKeys.length);
      cacheFiles = existingKeys;
    } else {
      cacheFiles = await cacheExports(initialisationCache, progressCallback);
      console.log("Refreshed the initialisation cache with new values", cacheFiles);
    }

    console.debug('cacheFiles are', cacheFiles);
    progressCallback("The data files have been downloaded, loading to the database : 13% complete", false);

    const perFilePercent = 85 / cacheFiles.length;
    for (const i in cacheFiles) {
      const file = cacheFiles[i];
      const response = await initialisationCache.get(file);
      console.debug("Trying to import reponse from cache for file", file)
      console.debug("The reponse object is", response)
      const content = JSON.parse(await response.text());

      console.debug(`Got content for ${file}`, content);
      const importResult = await db.definitions.bulkInsert(content);
      console.debug(`bulkImport for ${file} didn't fail! Now trying to remove`, importResult);

      await initialisationCache.remove(file);
      const newList = await initialisationCache.list();
      console.debug("All keys after delete of file", newList);
      const deleteResult = newList.filter(x => x == file).length == 0;

      console.debug(`${file} was successfully deleted ${deleteResult}? If so force immediate index refresh, if not, throw`);
      if (!deleteResult) {
        throw "deleteResult is false, that is unfortunate";
      }

      // force immediate index refresh so if we restart, we are already mostly ready
      await db.definitions.find().where('graph').eq(LOADED_QUERY_ENTRY).exec();

      console.debug(`Index refreshed after ${file}`);
      progressCallback(`Importing file ${i} : initialisation ${((perFilePercent * i) + 13).toFixed(2)}% complete`, false);

    }
  }
  // FIXME: delete the files db to make sure it doesn't accumulate cruft

  progressCallback("The data files have been loaded into the database : 98% complete", false);
  const cardsReplicationState = setupCardsReplication(db);  // FIXME: these should probably be generic
  const definitionsReplicationState = setupPullOnlyReplication(db.definitions, pullDefsQueryBuilder);
  const wordListsReplicationState = setupPullOnlyReplication(db.word_lists, pullWordListQueryBuilder);
  const wordModelStatsReplicationState = setupPullOnlyReplication(db.word_model_stats, pullWordModelStatsQueryBuilder);

  if (activateSubscription) {
    setupGraphQLSubscription(cardsReplicationState, CARD_CHANGED_QUERY);
    setupGraphQLSubscription(definitionsReplicationState, DEFINITION_CHANGED_QUERY);
    setupGraphQLSubscription(wordListsReplicationState, WORD_LIST_CHANGED_QUERY);
    setupGraphQLSubscription(wordModelStatsReplicationState, WORD_MODEL_STATS_CHANGED_QUERY);
  }
  return testQueries(db).then(doc => {
    console.debug(`Queried the db for ${LOADED_QUERY_ENTRY}:`, doc);
    progressCallback("The indexes have now been generated. The initialisation has finished! : 100% complete", true);
    return db;
  });
}

async function getDb(config, progressCallback) {
  console.debug('Loading config to database dbmulti', config);

  if (parseJwt(config.jwtRefreshToken).exp > parseJwt(jwtRefreshToken).exp) {
    jwtRefreshToken = config.jwtRefreshToken;
  }

  if (!dbPromise || !!config.reinitialise) {
    ({ username, syncURL, batchSize, wsEndpointUrl, jwtAccessToken, jwtRefreshToken } = config);
    dbPromise = loadFromExports(config, progressCallback);
  }
  return await dbPromise;
}

function createRxDBConfig(urlString, username, accessToken, refreshToken, cacheName, reinitialise=false, batchSize=10000) {
  console.debug("parameters in createRxDBConfig (urlString, username, accessToken, refreshToken, cacheName, reinitialise, batchSize)",
    urlString, username, accessToken, refreshToken, cacheName, reinitialise, batchSize);
  const url = new URL(urlString);
  return {
    username,
  	batchSize,
    cacheName,
  	syncURL: `${url.origin}/api/graphql`,
  	wsEndpointUrl: `ws${url.protocol == "https:" ? "s" : ""}://${url.host}/subscriptions`,
  	jwtAccessToken: accessToken,
  	jwtRefreshToken: refreshToken,
    reinitialise: reinitialise,
  	activateSubscription: true,
  	testDb: false,
  }
}

export {
  getDb,
  createRxDBConfig,
  getDatabaseName,
  deleteDatabase,
}
