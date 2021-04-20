
class AbstractWorkerProxy {
  constructor() {
    if (typeof this.sendMessage !== "function") { throw new TypeError("Must override sendMessage"); }
    if (typeof this.getURL !== "function") { throw new TypeError("Must override getURL"); }
  }
  sendMessage(_message, _callback) { throw new TypeError("Must override sendMessage"); }
  getURL(_message, _callback) { throw new TypeError("Must override getURL"); }
}

class ServiceWorkerProxy extends AbstractWorkerProxy{
  DATA_SOURCE = "ServiceWorkerProxy";

  #callbacks = {};
  #config = {};
  #messageQueue = [];

  #loaded = false;

  constructor() {
    super();
    navigator.serviceWorker.addEventListener('message', event => {
      const message = event.data;
      console.log(`The service worker client sent a message:`, message);
      const identifier = `${message.source}-${message.type}`;
      if (identifier in this.#callbacks){
        console.log(`doing the callback from sw in proxies.js message:`, message, this.#callbacks[identifier]);
        return this.#callbacks[identifier](message.value)
      } else {
        console.warn('Service Worker proxy received unknown event:', event)
        // FIXME: should I be a singleton and throw if I don't know the kind of message?
        // throw 'why you ask me for stuff i don know bout?'
      }
    });
    this.init = this.init.bind(this);
    this.sendMessage = this.sendMessage.bind(this);
    this.postMessage = this.postMessage.bind(this);
    this.getURL = this.getURL.bind(this);
  }
  getURL(relativePath) {
    return this.#config.resourceRoot.replace(/\/*$/, '') + '/' + relativePath.replace(/^\/*/, '')
  }

  postMessage([message, callback, progressCallback]) {
    const identifier = `${message.source}-${message.type}`;
    console.debug('Posting message from ServiceWorkerProxy to for identifier', identifier)

    if (identifier in this.#callbacks) {
      console.warn(`${identifier} already has a callback registered, overriding`, callback)
    }
    this.#callbacks[identifier] = callback;
    this.#callbacks[identifier + "-progress"] = progressCallback;
    return navigator.serviceWorker.ready.then(registration => {
      console.debug('Posting message from ServiceWorkerProxy to sw registration', message)
      message.appConfig = this.#config;  // add the appConfig, so the sw can reinit if needed
      registration.active.postMessage(message);
      return message;
    });
  }

  sendMessage(message, callback, progressCallback) {
    if (message.type == "isDbInitialised") {
      return callback(!!(localStorage.getItem('isDbInitialised')))
    } else if (message.type == "heartbeat") {
      this.postMessage([message, callback, progressCallback]);
      return;
    } else if (!this.#loaded && `${this.DATA_SOURCE}-${"syncDB"}` in this.#callbacks) {
      // we are not yet initialised, queue the messages rather than actually send them
      this.#messageQueue.push([message, callback, progressCallback]);
      return;
    } // else if !this.#initialised then throw error ???

    this.postMessage([message, callback, progressCallback]);
  }

  init(config, callback, progressCallback) {
    console.debug("Setting up ServiceWorkerProxy.init with config", config);
    this.#config = config;
    this.#config.resourceRoot = this.#config.resourceRoot || this.#config.resource_root;
    this.#config.isDbInitialised = localStorage.getItem('isDbInitialised');

    const message = { source: this.DATA_SOURCE, type: "syncDB", value: {} };  // appConfig gets added in postMessage
    return this.sendMessage(message, (response) => {
      console.debug(`Got a response for message in ServiceWorkerProxy init returning to caller`, message, response);
      this.#loaded = true;
      while (this.#messageQueue.length > 0) {
        this.postMessage(this.#messageQueue.shift());
      }
      return callback(response);
    }, (progress) => {
      console.debug('I am in the ServiceWorkerProxy progress callback with: ', progress)
      // Or should I be in the normal callback?
      if (progress.isFinished) {
        localStorage.setItem('isDbInitialised', 'true');
      }
      return progressCallback(progress);
    });
  }
}

class BackgroundWorkerProxy extends AbstractWorkerProxy {
  DATA_SOURCE = "BackgroundWorkerProxy";

  getURL = chrome.runtime.getURL;
  #callbacks = {};
  #config = {};
  #messageQueue = [];

  #loaded = false;

  constructor() {
    super();
    this.init = this.init.bind(this);
    this.sendMessage = this.sendMessage.bind(this);
    this.postMessage = this.postMessage.bind(this);
  }

  postMessage([message, callback, progressCallback]) {
    const identifier = `${message.source}-${message.type}`;

    if (identifier in this.#callbacks) {
      console.warn(`${identifier} already has a callback registered, overriding`, callback)
    }
    this.#callbacks[identifier] = callback;
    this.#callbacks[identifier + "-progress"] = progressCallback;

    console.debug('In postMessage, sending message', message)
    chrome.runtime.sendMessage(message, (returnMessage) => {
      console.debug('Calling callback in BackgroundWorkerProxy postMessage: message, returnMessage', message, returnMessage)
      return callback(returnMessage.value);
    })
  }

  sendMessage(message, callback, progressCallback) {
    console.debug('in sendMessage', this.#loaded, `${this.DATA_SOURCE}-${"syncDB"}`, this.#callbacks)
    if (!this.#loaded && `${this.DATA_SOURCE}-${"syncDB"}` in this.#callbacks) {
      // we are not yet initialised, queue the messages rather than actually send them
      this.#messageQueue.push([message, callback, progressCallback]);
      return;
    } // else if !this.#initialised then throw error ???

    return this.postMessage([message, callback, progressCallback]);
  }

  init(config, callback, progressCallback) {
    console.debug("Setting up BackgroundWorkerProxy.init with config", config);
    this.#config = config;
    this.#config.resourceRoot = this.#config.resourceRoot || this.#config.resource_root

    const message = { source: this.DATA_SOURCE, type: "syncDB", value: this.#config };
    return this.sendMessage(message, (response) => {
      console.debug(`Got a response for message in BackgroundWorkerProxy init returning to caller`, message, response);
      this.#loaded = true;
      while (this.#messageQueue.length > 0) {
        this.postMessage(this.#messageQueue.shift());
      }
      return callback(response);
    }
    , (progress) => { console.debug('I am in the progress callback with: ', progress); return progressCallback(progress); }
    );
  }
}

export {
  ServiceWorkerProxy,
  BackgroundWorkerProxy,
}
