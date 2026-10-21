/* Thread / ChatGenie messenger — loads async after page load so it never
   blocks rendering (blueprint performance rule). Widget served by
   messenger.chatgenie.io; appId is a public client-side identifier. */
(function () {
  'use strict';

  var chatgenieParams = {
    appId: "a20d40bb-64b1-45b7-991a-8156be58640e"
  };

  function run(ch) { ch.default.messenger().initialize(chatgenieParams); }

  function inject() {
    if (window.chatgenie) { run(window.chatgenie); return; }
    var t = document.createElement('script');
    t.type = 'text/javascript';
    t.async = true;
    t.onload = function () { if (window.chatgenie) run(window.chatgenie); };
    t.src = 'https://messenger.chatgenie.io/widget.js';
    var n = document.getElementsByTagName('script')[0];
    n.parentNode.insertBefore(t, n);
  }

  /* Original vendor snippet waits for window load; also handle the case where
     the document has already finished loading when this file runs. */
  if (document.readyState === 'complete') {
    inject();
  } else {
    window.addEventListener('load', inject, false);
  }
})();
