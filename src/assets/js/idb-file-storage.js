"use strict";
// Adapted from https://raw.githubusercontent.com/rpl/idb-file-storage/master/src/idb-file-storage.js
// with all the window and FF-specific references removed

/**
 * @typedef {Object} IDBFileStorage.ListFilteringOptions
 * @property {string} startsWith
 *   A string to be checked with `fileNameString.startsWith(...)`.
 * @property {string} endsWith
 *   A string to be checked with  `fileNameString.endsWith(...)`.
 * @property {string} includes
 *   A string to be checked with `fileNameString.includes(...)`.
 * @property {function} filterFn
 *   A function to be used to check the file name (`filterFn(fileNameString)`).
 */

/**
 * Wraps a DOMRequest into a promise, optionally transforming the result using the onsuccess
 * callback.
 *
 * @param {IDBRequest|DOMRequest} req
 *   The DOMRequest instance to wrap in a Promise.
 * @param {function}  [onsuccess]
 *   An optional onsuccess callback which can transform the result before resolving it.
 *
 * @returns {Promise}
 *   The promise which wraps the request result, rejected if the request.onerror has been
 *   called.
 */
export function waitForDOMRequest(req, onsuccess) {
  return new Promise((resolve, reject) => {
    req.onsuccess = onsuccess ?
      (() => resolve(onsuccess(req.result))) : (() => resolve(req.result));
    req.onerror = () => reject(req.error);
  });
}

/**
 * Provides a Promise-based API to store files into an IndexedDB.
 *
 * Instances of this class are created using the exported
 * {@link getFileStorage} function.
 */
export class IDBFileStorage {
  /**
   * @private private helper method used internally.
   */
  constructor({name, persistent} = {}) {
    // All the following properties are private and it should not be needed
    // while using the API.

    /** @private */
    this.name = name;
    /** @private */
    this.persistent = persistent;
    /** @private */
    this.indexedDBName = `IDBFilesStorage-DB-${this.name}`;
    /** @private */
    this.objectStorageName = "IDBFilesObjectStorage";
    /** @private */
    this.initializedPromise = undefined;

    // TODO: evalutate schema migration between library versions?
    /** @private */
    this.version = 1.0;
  }

  /**
   * @private private helper method used internally.
   */
  initializedDB() {
    if (this.initializedPromise) {
      return this.initializedPromise;
    }

    this.initializedPromise = (async () => {
      const dbReq = indexedDB.open(this.indexedDBName, this.version);

      dbReq.onupgradeneeded = () => {
        const db = dbReq.result;
        if (!db.objectStoreNames.contains(this.objectStorageName)) {
          db.createObjectStore(this.objectStorageName);
        }
      };

      return waitForDOMRequest(dbReq);
    })();

    return this.initializedPromise;
  }

  /**
   * @private private helper method used internally.
   */
  getObjectStoreTransaction({idb, mode} = {}) {
    const transaction = idb.transaction([this.objectStorageName], mode);
    return transaction.objectStore(this.objectStorageName);
  }

  /**
   * Put a file object into the IDBFileStorage, it overwrites an existent file saved with the
   * fileName if any.
   *
   * @param {string} fileName
   *   The key associated to the file in the IDBFileStorage.
   * @param {Blob|File} file
   *   The file to be persisted.
   *
   * @returns {Promise}
   *   A promise resolved when the request has been completed.
   */
  async put(fileName, file) {
    if (!fileName || typeof fileName !== "string") {
      throw new Error("fileName parameter is mandatory");
    }

    if (!(file instanceof File) && !(file instanceof Blob)) {
      throw new Error(`Unable to persist ${fileName}. Unknown file type.`);
    }

    const idb = await this.initializedDB();
    const objectStore = this.getObjectStoreTransaction({idb, mode: "readwrite"});
    return waitForDOMRequest(objectStore.put(file, fileName));
  }

  /**
   * Remove a file object from the IDBFileStorage.
   *
   * @param {string} fileName
   *   The fileName (the associated IndexedDB key) to remove from the IDBFileStorage.
   *
   * @returns {Promise}
   *   A promise resolved when the request has been completed.
   */
  async remove(fileName) {
    if (!fileName) {
      throw new Error("fileName parameter is mandatory");
    }

    const idb = await this.initializedDB();
    const objectStore = this.getObjectStoreTransaction({idb, mode: "readwrite"});
    return waitForDOMRequest(objectStore.delete(fileName));
  }

  /**
   * List the names of the files stored in the IDBFileStorage.
   *
   * (If any filtering options has been specified, only the file names that match
   * all the filters are included in the result).
   *
   * @param {IDBFileStorage.ListFilteringOptions} options
   *   The optional filters to apply while listing the stored file names.
   *
   * @returns {Promise<string[]>}
   *   A promise resolved to the array of the filenames that has been found.
   */
  async list(options) {
    const idb = await this.initializedDB();
    const objectStore = this.getObjectStoreTransaction({idb});
    const allKeys = await waitForDOMRequest(objectStore.getAllKeys());

    let filteredKeys = allKeys;

    if (options) {
      filteredKeys = filteredKeys.filter(key => {
        let match = true;

        if (typeof options.startsWith === "string") {
          match = match && key.startsWith(options.startsWith);
        }

        if (typeof options.endsWith === "string") {
          match = match && key.endsWith(options.endsWith);
        }

        if (typeof options.includes === "string") {
          match = match && key.includes(options.includes);
        }

        if (typeof options.filterFn === "function") {
          match = match && options.filterFn(key);
        }

        return match;
      });
    }

    return filteredKeys;
  }

  /**
   * Count the number of files stored in the IDBFileStorage.
   *
   * (If any filtering options has been specified, only the file names that match
   * all the filters are included in the final count).
   *
   * @param {IDBFileStorage.ListFilteringOptions} options
   *   The optional filters to apply while listing the stored file names.
   *
   * @returns {Promise<number>}
   *   A promise resolved to the number of files that has been found.
   */
  async count(options) {
    if (!options) {
      const idb = await this.initializedDB();
      const objectStore = this.getObjectStoreTransaction({idb});
      return waitForDOMRequest(objectStore.count());
    }

    const filteredKeys = await this.list(options);
    return filteredKeys.length;
  }

  /**
   * Retrieve a file stored in the IDBFileStorage by key.
   *
   * @param {string} fileName
   *   The key to use to retrieve the file from the IDBFileStorage.
   *
   * @returns {Promise<Blob|File>}
   *   A promise resolved once the file stored in the IDBFileStorage has been retrieved.
   */
  async get(fileName) {
    const idb = await this.initializedDB();
    const objectStore = this.getObjectStoreTransaction({idb});
    return waitForDOMRequest(objectStore.get(fileName)).then(result => {
      return result;
    });
  }

  /**
   * Remove all the file objects stored in the IDBFileStorage.
   *
   * @returns {Promise}
   *   A promise resolved once the IDBFileStorage has been cleared.
   */
  async clear() {
    const idb = await this.initializedDB();
    const objectStore = this.getObjectStoreTransaction({idb, mode: "readwrite"});
    return waitForDOMRequest(objectStore.clear());
  }
}

/**
 * Retrieve an IDBFileStorage instance by name (and it creates the indexedDB if it doesn't
 * exist yet).
 *
 * @param {Object} [param]
 * @param {string} [param.name="default"]
 *   The name associated to the IDB File Storage.
 * @param {boolean} [param.persistent]
 *   Optionally enable persistent storage mode (not enabled by default).
 *
 * @returns {IDBFileStorage}
 *   The IDBFileStorage instance with the given name.
 */
export async function getFileStorage({name, persistent} = {}) {
  const filesStorage = new IDBFileStorage({name: name || "default", persistent});
  await filesStorage.initializedDB();
  return filesStorage;
}

/**
 * @external {Blob} https://developer.mozilla.org/en-US/docs/Web/API/Blob
 */

/**
 * @external {DOMRequest} https://developer.mozilla.org/en/docs/Web/API/DOMRequest
 */

/**
 * @external {File} https://developer.mozilla.org/en-US/docs/Web/API/File
 */

/**
 * @external {IDBRequest} https://developer.mozilla.org/en-US/docs/Web/API/IDBRequest
 */
