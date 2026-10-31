/* Executive H5 Kit · reduced-motion preference, latest-task guard and number tween. */
(function (global) {
  'use strict';

  var media = global.matchMedia ? global.matchMedia('(prefers-reduced-motion: reduce)') : { matches: false };
  var override = null;
  var listeners = [];
  var tweenStates = new WeakMap();
  var activeTweens = new Set();

  function preference() {
    var reduced = !!media.matches || override === 'reduce';
    return { reduced: reduced, systemReduced: !!media.matches, override: override };
  }

  function notify() {
    var value = preference();
    document.documentElement.dataset.motion = value.reduced ? 'reduced' : 'full';
    if (value.reduced) {
      Array.from(activeTweens).forEach(function (state) { state.finish(); });
    }
    listeners.slice().forEach(function (listener) { listener(value); });
  }

  function setOverride(value) {
    if (value !== null && value !== 'reduce' && value !== 'full') {
      throw new Error('setOverride: expected null, reduce or full');
    }
    override = value;
    notify();
  }

  function subscribe(listener, immediate) {
    listeners.push(listener);
    if (immediate !== false) listener(preference());
    return function () { listeners = listeners.filter(function (item) { return item !== listener; }); };
  }

  function onMediaChange() { notify(); }
  if (media.addEventListener) media.addEventListener('change', onMediaChange);
  else if (media.addListener) media.addListener(onMediaChange);
  notify();

  function createLatest() {
    var current = 0;
    return {
      next: function () {
        var id = ++current;
        return { id: id, isCurrent: function () { return id === current; } };
      },
      invalidate: function () { current += 1; },
      current: function () { return current; }
    };
  }

  function tweenNumber(element, to, options) {
    options = options || {};
    var format = options.format || function (value) { return String(value); };
    var finalText = format(to);
    element.setAttribute('aria-label', finalText);
    var previous = tweenStates.get(element);
    if (previous && previous.cancel) previous.cancel();
    var from = previous && typeof previous.value === 'number' ? previous.value :
      (typeof options.from === 'number' ? options.from : 0);
    var state = { value: from, cancelled: false, frame: 0 };
    state.cancel = function () {
      state.cancelled = true;
      if (state.frame) cancelAnimationFrame(state.frame);
      activeTweens.delete(state);
    };
    state.finish = function () {
      if (state.cancelled) return;
      state.cancelled = true;
      if (state.frame) cancelAnimationFrame(state.frame);
      state.value = to;
      state.frame = 0;
      element.textContent = finalText;
      activeTweens.delete(state);
    };
    tweenStates.set(element, state);
    activeTweens.add(state);

    if (preference().reduced || options.duration === 0 || from === to) {
      state.finish();
      return state.cancel;
    }

    var duration = options.duration || 420;
    var start = performance.now();
    function frame(now) {
      if (state.cancelled) return;
      var progress = Math.min(1, (now - start) / duration);
      var eased = 1 - Math.pow(1 - progress, 3);
      state.value = from + (to - from) * eased;
      element.textContent = progress === 1 ? finalText : format(state.value);
      if (progress < 1) state.frame = requestAnimationFrame(frame);
      else state.finish();
    }
    state.frame = requestAnimationFrame(frame);
    return state.cancel;
  }

  function scrollTo(options) {
    options = options || {};
    global.scrollTo({
      top: options.top || 0,
      left: options.left || 0,
      behavior: preference().reduced ? 'auto' : (options.behavior || 'auto')
    });
  }

  global.H5Motion = {
    preference: preference,
    setOverride: setOverride,
    subscribe: subscribe,
    createLatest: createLatest,
    tweenNumber: tweenNumber,
    scrollTo: scrollTo
  };
})(window);
