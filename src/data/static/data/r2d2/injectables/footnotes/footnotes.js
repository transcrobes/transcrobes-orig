var Footnotes=function(e){var t={};function n(o){if(t[o])return t[o].exports;var r=t[o]={i:o,l:!1,exports:{}};return e[o].call(r.exports,r,r.exports,n),r.l=!0,r.exports}return n.m=e,n.c=t,n.d=function(e,t,o){n.o(e,t)||Object.defineProperty(e,t,{enumerable:!0,get:o})},n.r=function(e){"undefined"!=typeof Symbol&&Symbol.toStringTag&&Object.defineProperty(e,Symbol.toStringTag,{value:"Module"}),Object.defineProperty(e,"__esModule",{value:!0})},n.t=function(e,t){if(1&t&&(e=n(e)),8&t)return e;if(4&t&&"object"==typeof e&&e&&e.__esModule)return e;var o=Object.create(null);if(n.r(o),Object.defineProperty(o,"default",{enumerable:!0,value:e}),2&t&&"string"!=typeof e)for(var r in e)n.d(o,r,function(t){return e[t]}.bind(null,r));return o},n.n=function(e){var t=e&&e.__esModule?function(){return e.default}:function(){return e};return n.d(t,"a",t),t},n.o=function(e,t){return Object.prototype.hasOwnProperty.call(e,t)},n.p="",n(n.s=0)}([function(e,t,n){"use strict";n.r(t),n.d(t,"IS_DEV",(function(){return r}));var o=function(e,t,n,o){return new(n||(n=Promise))((function(r,i){function a(e){try{l(o.next(e))}catch(e){i(e)}}function c(e){try{l(o.throw(e))}catch(e){i(e)}}function l(e){var t;e.done?r(e.value):(t=e.value,t instanceof n?t:new n((function(e){e(t)}))).then(a,c)}l((o=o.apply(e,t||[])).next())}))};const r=!1;document.addEventListener("click",e=>o(void 0,void 0,void 0,(function*(){r&&console.log("Footnote Click Handler");var t=e.target;if("a"===t.tagName.toLowerCase()){var n=document.createElement("div");n.innerHTML=t.outerHTML;var i=n.querySelector("a");if(i)if("noteref"==i.getAttribute("epub:type")){var a=i.getAttribute("href");if(a.indexOf("#")>0){var c=a.substring(a.indexOf("#")+1),l=function(e){var t=document.location.href;return new URL(e,t).href}(a);l=l.substring(0,l.indexOf("#")),e.preventDefault(),e.stopPropagation(),yield fetch(l).then(e=>e.text()).then(e=>o(void 0,void 0,void 0,(function*(){var n=(new DOMParser).parseFromString(e,"text/html").querySelector("aside#"+c);if(n){var o=document.createElement("div");o.className="modal",o.innerHTML='<div class="modal-content"><span class="close">x</span>'+n.innerHTML+"</div>",o.style.display="block",document.body.appendChild(o);var r=o.getElementsByClassName("modal-content")[0],a=t.offsetTop;t.offsetTop>100&&(a=t.offsetTop-20),r.style.top=a+"px",o.getElementsByClassName("close")[0].onclick=function(){o.style.display="none",o.parentElement.removeChild(o)},window.onclick=function(e){e.target==o&&(o.style.display="none",o.parentElement.removeChild(o))}}else i.click()})))}}}})),!0)}]);
//# sourceMappingURL=footnotes.js.map