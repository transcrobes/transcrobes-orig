
const CACHE_NAME = "v1";
const INITIALISATION_CACHE_NAME = `${CACHE_NAME}.initialisation`;

function wordId(card) {
  return card.cardId.split(CARD_ID_SEPARATOR)[0];
}
function cardType(card) {
  return card.cardId.split(CARD_ID_SEPARATOR)[1];
}

const EVENT_QUEUE_SCHEMA = {
  version: 0,
  type: 'object',
  properties: {
    eventTime: {
      type: 'string',
      primary: true
    },
    eventString: {
      type: 'string',
    }
  }
}

const CONTENT_CONFIG_SCHEMA = {
  version: 0,
  type: 'object',
  properties: {
    contentId: {
      type: 'string',
      primary: true
    },
    configString: {
      type: 'string',
    }
  }
}

const WORD_SCHEMA = {
  version: 0,
  type: 'object',
  properties: {
    wordId: {
      type: 'string',
      primary: true
    },
    graph: {
      type: 'string'
    },
    sound: {
      type: "array",
      items: {
        type: 'string'
      }
    },
    synonyms: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          posTag: {
            type: "string"
          },
          values: {
            type: 'array',
            items: {
              type: "string"
            }
          },
        }
      }
    },
    providerTranslations: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          provider: {
            type: "string"
          },
          posTranslations: {
            type: 'array',
            items: {
              type: 'object',
              properties: {
                posTag: {
                  type: "string"
                },
                values: {
                  type: 'array',
                  items: {
                    type: "string"
                  }
                },
              }
            }
          }
        }
      }
    },
    frequency: {
      //{"pinyin": "de/dí/dì", "wcpm": "50155.13", "wcdp": "100", "pos": ".u.n.", "pos_freq": ".1682369.161."}
      type: 'object',
      properties: {
        wcpm: {
          type: "string"  // could be int
        },
        wcdp: {
          type: "string"  // could be int
        },
        pos: {
          type: "string"
        },
        pos_freq: {
          type: "string"
        }
      },
      // required: ['wcpm', 'wcdp', 'pos', 'pos_freq']  // FIXME: what will this do to perf?
    },
    hsk: {
      type: 'object',
      properties: {
        levels: {
          type: "array",
          items: {
            type: "integer"
          }
        },
      },
    },
    updatedAt: {
      type: 'number'
    },
  },
  indexes: ['updatedAt', 'graph'],
  // required: ['graph', 'sound', 'definition', 'updatedAt']
};

const CHARACTER_SCHEMA = {
  version: 0,
  type: 'object',
  properties: {
    graph: {
      type: 'string',
      primary: true
    },
    structure: {  // from https://github.com/chanind/hanzi-writer
      type: 'string'
    },
  }
}

const WORD_LIST_SCHEMA = {
  version: 0,
  type: 'object',
  properties: {
    listId: {
      type: 'string',
      primary: true
    },
    name: {
      type: 'string',
    },
    default: {
      type: 'boolean',
      default: false,
    },
    wordIds: {
      type: "array",
      items: {
        type: 'string'
      }
    },
    updatedAt: {
      type: 'number'
    }
  },
  indexes: ['updatedAt'],
};

const WORD_MODEL_STATS_SCHEMA = {
  version: 0,
  type: 'object',
  properties: {
    wordId: {
      type: 'string',
      primary: true
    },
    nbSeen: {
      type: 'integer'
    },
    nbSeenSinceLastCheck: {
      type: 'integer'
    },
    lastSeen: {
      type: 'number'
    },
    nbChecked: {
      type: 'integer'
    },
    lastChecked: {
      type: 'number'
    },
    nbTranslated: {
      type: ['integer', 'null']
    },
    lastTranslated: {
      type: ['integer', 'null']
    },
    updatedAt: {
      type: 'number'
    }
  },
  indexes: ['updatedAt'],
};

const CARD_ID_SEPARATOR = '-';
const EFACTOR_DEFAULT = 2.5;
const GRADE = {
  UNKNOWN: 2,
  HARD: 3,
  GOOD: 4,
  KNOWN: 5,
  gradeName : function(grade) {
    const name = Object.entries(this).find(i => i[1].toString() === grade.toString())
    return name ? name[0].toLowerCase() : undefined;
  },
}
const DEFAULT_BAD_REVIEW_WAIT_SECS = 600;

const CARD_TYPES = {
  GRAPH: 1,
  SOUND: 2,
  MEANING: 3,
  cardName : function(cardType) {
    const name = Object.entries(this).find(i => i[1].toString() === cardType.toString());
    return name ? name[0].toLowerCase() : undefined;
  },
  typeIds : function() {
    return Object.entries(CARD_TYPES).filter(([_l, v]) => !(v instanceof Function))
      .map(([_l, id]) => { return id });
  },

};

const CARD_SCHEMA = {
  version: 3,
  type: 'object',
  properties: {
    // "{word_id}-{card_type}" - card_type: 1 = L2 written form, 2 = L2 sound representation, 3 = L1 definition
    cardId: {
      type: 'string',
      primary: true
    },
    dueDate: {
      type: 'number'
    },
    interval: {
      type: 'integer',
      default: 0
    },
    repetition: {
      type: 'integer',
      default: 0
    },
    efactor: {
      type: 'number',
      default: EFACTOR_DEFAULT
    },
    front: {  // manual personalised card front, i.e, not just default generated from the dict
      type: 'string'
    },
    back: {  // manual personalised card back, i.e, not just default generated from the dict
      type: 'string'
    },
    suspended: {
      type: 'boolean',
      default: false,
    },
    known: {
      type: 'boolean',
      default: false,
    },
    firstRevisionDate: {
      type: 'number',
      default: 0,
    },
    lastRevisionDate: {
      type: 'number',
      default: 0,
    },
    updatedAt: {
      type: 'number'
    }
  },
  indexes: ['lastRevisionDate', 'dueDate', 'firstRevisionDate', 'suspended'],
  // required: ['cardType']
};

const graphQLGenerationInput = {
  wordList: {
    schema: WORD_LIST_SCHEMA,
    feedKeys: [
      'listId',
      'updatedAt'
    ],
    deletedFlag: 'deleted',
    subscriptionParams: {
      token: 'String!'
    }
  },
  card: {
    schema: CARD_SCHEMA,
    feedKeys: [
      'cardId',
      'updatedAt'
    ],
    deletedFlag: 'deleted',
    subscriptionParams: {
      token: 'String!'
    }
  },
  definition: {
    schema: WORD_SCHEMA,
    feedKeys: [
      'wordId',
      'updatedAt'
    ],
    deletedFlag: 'deleted',
    subscriptionParams: {
      token: 'String!'
    }
  },
  wordModelStats: {
    schema: WORD_MODEL_STATS_SCHEMA,
    feedKeys: [
      'wordId',
      'updatedAt'
    ],
    deletedFlag: 'deleted',
    subscriptionParams: {
      token: 'String!'
    }
  }
};

export {
  // RxDB schemata
  CONTENT_CONFIG_SCHEMA,
  EVENT_QUEUE_SCHEMA,
  WORD_SCHEMA,
  WORD_LIST_SCHEMA,
  WORD_MODEL_STATS_SCHEMA,
  CARD_SCHEMA,
  CHARACTER_SCHEMA,

  CARD_ID_SEPARATOR,
  GRADE,
  CARD_TYPES,
  EFACTOR_DEFAULT,
  DEFAULT_BAD_REVIEW_WAIT_SECS,
  CACHE_NAME,
  INITIALISATION_CACHE_NAME,
  graphQLGenerationInput,
  cardType,
  wordId,
}
