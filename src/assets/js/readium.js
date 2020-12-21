import * as components from './components.js';
export * from './components.js';

const platformHelper = parent.window.wproxy;
components.setPlatformHelper(platformHelper);


function showHideMenus(event){
  if (!components.destroyPopup(event, document, window.parent.document)) {
    if (window.parent.document.querySelector("#headerMenu").classList.contains('hidden')) {
      window.parent.document.querySelector("#headerMenu").classList.remove("hidden");
      window.parent.document.querySelector("iframe").height = window.parent.iframeHeight;
    } else {
      window.parent.document.querySelector("#headerMenu").classList.add("hidden");
      window.parent.document.querySelector("iframe").height = (window.parent.innerHeight - 20) + "px";
    }
    window.parent.document.querySelector("#container-view-timeline").classList.toggle("hidden");
    window.parent.document.querySelector("#reader-info-bottom-wrapper").classList.toggle("hidden");
  } else {
      event.stopPropagation();  // we don't want other events, but we DO want the default, for clicking on links
  }
}
document.addEventListener('click', (event) => {
  showHideMenus(event)
});

// TODO: this also applies on the menus, whereas we just want on the "empty" space under the iframe
// window.parent.document.addEventListener('click', (event) => {
//   showHideMenus(event)
// });

components.setEventSource('readium-js');

components.setBaseUrl(window.location.origin);
components.setSegmentation(window.parent.segmentation);
components.setGlossing(window.parent.glossing);
components.setLangPair(window.parent.langPair);
components.setPopupParent(window.parent.document.body);

console.debug('Trying to sync in readium.js');

components.getUserCardWords().then(()=>{
  components.defineElements();
  console.log('Finished setting up elements for readium');
});
