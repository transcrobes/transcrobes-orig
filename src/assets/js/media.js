import * as components from './components.js';

export { toggleFullscreen } from './lib.js';
export { defineElements, getUserCardWords, setLangPair } from './components.js';

const ONSCREEN_DELAY_IS_CONSIDERED_READ = 1000; // milliseconds
const SAVE_CONFIG_TO_LOCAL_EVERY = 5000; // milliseconds

const DATA_SOURCE = 'media-js';
components.setEventSource(DATA_SOURCE);
const platformHelper = window.wproxy;

let parameters;
const videoPlayer = document.querySelector('#video-player');
const video = document.querySelector('#videoElement')
const videoWrapper = document.querySelector('#videoWrapper');
const playPauseButton = document.querySelector('.toggle-play-pause');
const startTimeLabel = document.querySelector('.start-time');
const endTimeLabel = document.querySelector('.end-time');
const videoSeekbar = document.querySelector('.video-seekbar');
const videoProgress = document.querySelector('.video-seekbar .progress');
const volumeToggle = document.querySelector('.toggle-volume');

const subtitleCanvas = document.querySelector('#subsDiv');
const subtitleDelayLabel = document.querySelector('#currentSubDelay');
const subtitleFontSizeLabel = document.querySelector('#currentFontSize');
const playbackRateLabel = document.querySelector('#currentPlaybackRate');
const subtitleBoxWidthLabel = document.querySelector('#currentSubBoxWidth');
const volumeLabel = document.querySelector('#currentVolume');

const AudioContext = window.AudioContext || window.webkitAudioContext;
let audioCtx;
let source;
let gainNode;

let totalDurationInSeconds = 0;
let currentDuration = null;
let totalDuration = null;
let seekPercentage = 0;

setInterval(() => {
    platformHelper.sendMessage({
      source: DATA_SOURCE,
      type: "setContentConfigToStore",
      value: parameters,
    }, (response) => {
      console.debug("Persisted mediaplayer state to storage with message", response)
    });
}, SAVE_CONFIG_TO_LOCAL_EVERY);

function getPercentage(presentTime, totalTime) {
  var calcPercentage = (presentTime / totalTime) * 100;
  return parseFloat(calcPercentage.toString());
};

function calculateDuration(duration) {
  var seconds = parseInt(duration % 60);
  var minutes = parseInt((duration % 3600) / 60);
  var hours = parseInt(duration / 3600);

  return {
    hours: pad(hours),
    minutes: pad(minutes.toFixed()),
    seconds: pad(seconds.toFixed())
  };
};

function pad(number){
  if (number > -10 && number < 10) {
    return '0' + number;
  } else {
    return number;
  }
};

/*-------------- UPDATE FUNCTIONS ---------------*/
const updateSeekbar = () => {
  seekPercentage = getPercentage(
    parameters.currentTime,
    totalDurationInSeconds
  );
  videoProgress.style.width = `${seekPercentage}%`;
};

const updateTotalDuration = () => {
  endTimeLabel.innerHTML = `${totalDuration.hours}:${totalDuration.minutes}:${totalDuration.seconds}`;
};

const updateCurrentTime = () => {
  startTimeLabel.innerHTML = `${currentDuration.hours}:${currentDuration.minutes}:${currentDuration.seconds}`;
};
/*----------- UPDATE FUNCTIONS -----------------*/

function initPositions(){
  if (video.textTracks) {
    if (parameters.subtitleDelay != 0) {
      Array.from(video.textTracks[0].cues).forEach((cue) => {  // add 0.5s to cue times
        cue.startTime += parameters.subtitleDelay; cue.endTime += parameters.subtitleDelay;
      });
    }
    console.log(parameters.currentTime);
    video.currentTime = parameters.currentTime;
    video.playbackRate = parameters.playbackRate;
  }
}

function stopPropagation(e) {
  video.focus();
  console.log(e);
  e.preventDefault();
  e.stopPropagation();
  return false;
}

function togglePause() {
  console.debug('running pause');
  playPauseButton.classList.contains('play')
    ? video.play()
    : video.pause();
  playPauseButton.classList.toggle('play');
  playPauseButton.classList.toggle('pause');
  return true;
}

function previousCue() {
  console.debug('running previousCue');
  const cues = Array.from(video.textTracks[0].cues)
  let low = 0; let high = cues.length;
  while (low < high) {
    const mid = (low + high)/2 | 0;
    if (video.currentTime > cues[mid].startTime) {
      low = mid + 1;
    } else {
      high = mid;
    }
  }
  low = low - 1 > 0 ? low - 1 : 0
  let previousStart = cues[low].startTime;
  if (video.currentTime - previousStart < 2) {
    video.currentTime = low > 0 ? cues[low-1].startTime : cues[0].startTime;
  } else {
    video.currentTime = previousStart;
  }
  return true;
}

function nextCue() {
  console.debug('running nextCue');
  const cues = Array.from(video.textTracks[0].cues)
  let low = 0; let high = cues.length;
  while (low < high) {
    const mid = (low + high)/2 | 0;
    if (video.currentTime < cues[mid].startTime) {
      high = mid;
    } else {
      low = mid + 1;
    }
  }
  video.currentTime = cues[low].startTime;
  return true;
}

function updateControls() {
  subtitleDelayLabel.textContent = (parameters.subtitleDelay <= 0 ? "" : "+") + parameters.subtitleDelay.toFixed(2);
  subtitleFontSizeLabel.textContent = `${parameters.fontSize}%`;
  playbackRateLabel.textContent = parameters.playbackRate.toFixed(2);
  volumeLabel.textContent = parameters.volumeValue.toFixed(2);
  subtitleBoxWidthLabel.textContent = `${parameters.subBoxWidth}%`;

  subtitleCanvas.style.fontSize = `${parameters.fontSize}%`;
  subtitleCanvas.style.maxWidth = `${parameters.subBoxWidth}%`;
  video.playbackRate = parameters.playbackRate.toFixed(2);
  if (gainNode) {
    console.debug('setting gain ' + parameters.volumeValue.toFixed(2));
    gainNode.gain.value = parameters.volumeValue.toFixed(2);
  }

  if (parameters.currentTime && video.currentTime && Math.abs(parameters.currentTime - video.currentTime) > 1) {
    video.currentTime = parameters.currentTime;
  }
}

function delaySubtitle(secs=0.5) {
  console.debug('running delaySubtitle');
  parameters.subtitleDelay -= secs;
  Array.from(video.textTracks[0].cues).forEach((cue) => {  // remove 0.5s from cue times
    cue.startTime -= secs; cue.endTime -= secs;
  });

  updateControls(video.ownerDocument);
  return true;
}

function advanceSubtitle(secs=0.5) {
  console.debug('running advanceSubtitle');
  parameters.subtitleDelay += secs;
  Array.from(video.textTracks[0].cues).forEach((cue) => {  // add 0.5s to cue times
    cue.startTime += secs; cue.endTime += secs;
  });
  updateControls(video.ownerDocument);
  return true;
}

function decreaseSubBoxWidth(subsDiv, percent=5) {
  console.debug('running decreaseSubBoxWidth');
  parameters.subBoxWidth -= percent;
  updateControls(subsDiv.ownerDocument);
  return true;
}

function increaseSubBoxWidth(subsDiv, percent=5) {
  console.debug('running increaseSubBoxWidth');
  parameters.subBoxWidth += percent;
  updateControls(subsDiv.ownerDocument);
  return true;
}

function decreaseFontSize(subsDiv, percent=10) {
  console.debug('running decreaseFontSize');
  parameters.fontSize -= percent;
  components.setFontSize(parameters.fontSize);
  updateControls(subsDiv.ownerDocument);
  return true;
}

function increaseFontSize(subsDiv, percent=10) {
  console.debug('running increaseFontSize');
  parameters.fontSize += percent;
  components.setFontSize(parameters.fontSize);
  updateControls(subsDiv.ownerDocument);
  return true;
}

function skipBack(secs=5) {
  console.debug('running skipBack');
  parameters.currentTime -= secs;  //back 5s, doesn't work in Chrome when server doesn't send Accept-Ranges
  updateControls(video.ownerDocument);
  return true;
}

function skipForward(secs=5) {
  console.debug('running skipForward');
  parameters.currentTime += secs;  //forward 5s, doesn't work in Chrome when server doesn't send Accept-Ranges
  updateControls(video.ownerDocument);
  return true;
}

function speedUp(ratio=0.05) {
  console.debug('running speedUp');
  parameters.playbackRate += ratio;  // speed up by ratio
  updateControls(video.ownerDocument);
  return true;
}

function slowDown(ratio=0.05) {
  console.debug('running slowDown');
  parameters.playbackRate -= ratio;  // slow down by ratio
  updateControls(video.ownerDocument);
  return true;
}

function increaseVolume(ratio=0.05) {
  console.debug('running increaseVolume');
  parameters.volumeValue += ratio;  // increase volume by ratio
  if (parameters.volumeValue > 3.4) parameters.volumeValue = 3.4;
  updateControls(video.ownerDocument);
  return true;
}

function decreaseVolume(ratio=0.05) {
  console.debug('running decreaseVolume');
  parameters.volumeValue -= ratio;  // decrease volume by ratio
  if (parameters.volumeValue < 0) parameters.volumeValue = 0;
  updateControls(video.ownerDocument);
  return true;
}

// function setupMedia(contentId, glossing, segmentation, theme, fontSize, subBoxWidth, resourceRoot) {
function setupMedia(contentId, glossing, segmentation, theme, fontSize, subBoxWidth) {
  console.log(`contentId, glossing, segmentation, theme, fontSize, subBoxWidth`, contentId, glossing, segmentation, theme, fontSize, subBoxWidth)

  document.body.classList.add(theme);
  components.setPlatformHelper(platformHelper);
  components.defineElements();
  console.debug('Finished setting up elements');

  platformHelper.sendMessage({ source: DATA_SOURCE, type: "getContentConfigFromStore", value: contentId.toString() },
      (savedParameters) => {
    console.debug(`savedParameters`, savedParameters);
    parameters = Object.entries(savedParameters || {}).length > 0 ? savedParameters : {
        contentId: contentId,
        fontSize: fontSize,
        subBoxWidth: subBoxWidth,
        currentTime: 0,
        subtitleDelay: 0,
        playbackRate: 1,
        volumeValue: 1,
      };
    console.debug(`parameters`, parameters);

    components.setPopupParent(videoWrapper);
    // FIXME: this is nastiness
    components.setBaseUrl(window.location.origin);
    components.setGlossing(glossing);
    components.setFontSize(parameters.fontSize);
    components.setSegmentation(segmentation);
    components.setOnScreenDelayIsConsideredRead(ONSCREEN_DELAY_IS_CONSIDERED_READ);
    updateControls(document);
  });
  //b});

  var keyListener = (e) => {
    if (e.key == 'f') {  // f key
      return components.toggleFullscreen(document, videoWrapper) && stopPropagation(e);
    } else if (e.key == " ") {  // space bar
      return togglePause() && stopPropagation(e);  // pause and play
    } else if (e.ctrlKey && e.shiftKey && e.key == "ArrowLeft") { // ctrl + shift + left
      return slowDown() && stopPropagation(e);
    } else if (e.ctrlKey && e.shiftKey && e.key == "ArrowRight") { // ctrl + shift + right
      return speedUp(0.05) && stopPropagation(e);
    } else if (e.shiftKey && e.key == "ArrowLeft") { // shift + left
      return delaySubtitle() && stopPropagation(e);
    } else if (e.shiftKey && e.key == "ArrowRight") { // shift + right
      return advanceSubtitle() && stopPropagation(e);
    } else if (e.ctrlKey && e.key == "ArrowLeft") { // ctrl + left
      return skipBack(5) && stopPropagation(e);
    } else if (e.ctrlKey && e.key == "ArrowRight") { // ctrl + right
      return skipForward(5) && stopPropagation(e);
    } else if (e.key == "ArrowLeft") {  // left
      return previousCue() && stopPropagation(e);  // seek to previous cue
    } else if (e.key == "ArrowRight") {  // right
      return nextCue() && stopPropagation(e);  // seek to next cue
    }
  };
  document.addEventListener("keydown", keyListener, true);
}

function setupPlayer(doc) {
  /*-------------- HIDE / SHOW CONTROLS -----------*/
  videoPlayer.onmouseover = () => {
    videoPlayer.classList.remove('hide-controls')
  };
  videoPlayer.onmouseleave = () => {
    if (!video.paused) {
      videoPlayer.classList.add('hide-controls');
    }
  }
  /*--------------- HIDE / SHOW CONTROLS --------*/

  //1. update the total duration
  video.onloadeddata = () => {
    totalDurationInSeconds = video.duration;
    totalDuration = calculateDuration(totalDurationInSeconds);
    updateTotalDuration();
    updateSeekbar();
  }

  // 2. update current time
  video.ontimeupdate = () => {
    parameters.currentTime = video.currentTime;
    currentDuration = calculateDuration(parameters.currentTime);
    updateCurrentTime();
    updateSeekbar();
  }
  video.onended = () => {
    video.currentTime = 0;
    playPauseButton.classList.remove('pause');
    playPauseButton.classList.add('play');
    videoPlayer.classList.remove('hide-controls');
  }
  /*----------------------user events ------------------------------*/

  //3. play the video
  playPauseButton.onclick = () => {
    playPauseButton.classList.contains('play')
      ? video.play()
      : video.pause();
    playPauseButton.classList.toggle('play');
    playPauseButton.classList.toggle('pause');
  }

  //5. toggle volume
  volumeToggle.onclick = () => {
    console.log(parameters.volumeValue);
    video.volume = video.volume ? 0 : 1;
    volumeToggle.classList.toggle('on');
    volumeToggle.classList.toggle('off');
  }

  //6. seekbar click
  videoSeekbar.onclick = (e) => {
    let tempSeekPosition = e.pageX - videoPlayer.offsetLeft - videoSeekbar.offsetLeft;
    let tempSeekValue = tempSeekPosition / videoSeekbar.clientWidth;
    video.currentTime = tempSeekValue * totalDurationInSeconds;
  };

  video.onplay = () => {
    playPauseButton.classList.remove('play');
    playPauseButton.classList.add('pause');
    if (!audioCtx) {
      audioCtx = new AudioContext();
      source = audioCtx.createMediaElementSource(video);
      gainNode = audioCtx.createGain();
      gainNode.gain.value = parameters.volumeValue;
      source.connect(gainNode);
      gainNode.connect(audioCtx.destination);
    }
  }
}

export {
  stopPropagation,
  togglePause,
  previousCue,
  nextCue,
  delaySubtitle,
  advanceSubtitle,
  increaseFontSize,
  decreaseFontSize,
  increaseSubBoxWidth,
  decreaseSubBoxWidth,
  increaseVolume,
  decreaseVolume,
  skipBack,
  skipForward,
  speedUp,
  slowDown,
  setupMedia,
  initPositions,
  setupPlayer,
}
