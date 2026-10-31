/* Executive H5 Kit · ECharts role-token bridge and motion defaults.
   Load motion.js first. For modular ECharts builds, register AriaComponent separately. */
(function (global) {
  'use strict';

  function css(element, name) {
    return getComputedStyle(element).getPropertyValue(name).trim();
  }

  function tokens(element) {
    element = element || document.documentElement;
    return {
      text1: css(element, '--h5-text-1') || '#142B3A',
      text2: css(element, '--h5-text-2') || '#425866',
      text3: css(element, '--h5-text-3') || '#65757F',
      surface: css(element, '--h5-surface-1') || '#FFFFFF',
      border: css(element, '--h5-border') || '#C8D3DA',
      current: css(element, '--h5-data-current') || '#175CD3',
      reference: css(element, '--h5-data-reference') || '#73848F',
      positive: css(element, '--h5-status-positive') || '#146C5A',
      negative: css(element, '--h5-status-negative') || '#A63D49',
      warning: css(element, '--h5-status-warning') || '#80550F',
      font: css(element, '--h5-font-body') || 'sans-serif',
      categories: [1, 2, 3, 4].map(function (index) { return css(element, '--h5-cat-' + index); }).filter(Boolean)
    };
  }

  function motionPreference() {
    return global.H5Motion ? global.H5Motion.preference() : { reduced: false };
  }

  function baseOption(element, options) {
    options = options || {};
    var t = tokens(element);
    var reduced = motionPreference().reduced;
    var palette = t.categories.length ? t.categories : [t.current, t.reference];
    return {
      animation: !reduced,
      animationDuration: reduced ? 0 : (options.enterDuration || 520),
      animationEasing: 'cubicOut',
      animationDurationUpdate: reduced ? 0 : (options.updateDuration || 280),
      animationEasingUpdate: 'cubicOut',
      animationThreshold: options.threshold || 1500,
      color: palette,
      textStyle: { fontFamily: t.font, color: t.text2 },
      aria: { show: true },
      grid: { left: 16, right: 20, top: 36, bottom: 12, containLabel: true },
      tooltip: {
        backgroundColor: t.surface,
        borderColor: t.border,
        borderWidth: 1,
        textStyle: { color: t.text1, fontFamily: t.font },
        confine: true
      },
      xAxis: {
        axisLine: { lineStyle: { color: t.border } },
        axisTick: { show: false },
        axisLabel: { color: t.text2, fontSize: 12 },
        splitLine: { show: false }
      },
      yAxis: {
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: t.text2, fontSize: 12 },
        splitLine: { lineStyle: { color: t.border, opacity: .55, type: 'dashed' } }
      }
    };
  }

  function motionOption(reduced) {
    return {
      animation: !reduced,
      animationDuration: reduced ? 0 : 520,
      animationDurationUpdate: reduced ? 0 : 280
    };
  }

  function applyMotion(chart, reduced) {
    if (chart && !chart.isDisposed()) chart.setOption(motionOption(reduced));
  }

  function update(chart, option, options) {
    options = options || {};
    var settings = {
      notMerge: !!options.replace,
      lazyUpdate: options.lazy !== false
    };
    if (options.replaceMerge) settings.replaceMerge = options.replaceMerge;
    chart.setOption(option, settings);
  }

  function resizeVisible(charts) {
    charts.forEach(function (chart) {
      if (!chart || chart.isDisposed()) return;
      var dom = chart.getDom();
      if (dom && dom.clientWidth > 0 && dom.clientHeight > 0 && dom.getClientRects().length) chart.resize();
    });
  }

  function createResizeObserver(charts) {
    var frame = 0;
    function schedule() {
      if (frame) return;
      frame = requestAnimationFrame(function () {
        frame = 0;
        resizeVisible(typeof charts === 'function' ? charts() : charts);
      });
    }
    var observer = global.ResizeObserver ? new ResizeObserver(schedule) : null;
    var observed = [];
    if (observer) {
      (typeof charts === 'function' ? charts() : charts).forEach(function (chart) {
        if (chart && chart.getDom()) {
          observer.observe(chart.getDom());
          observed.push(chart.getDom());
        }
      });
    }
    global.addEventListener('resize', schedule, { passive: true });
    schedule();
    return function () {
      if (frame) cancelAnimationFrame(frame);
      if (observer) observer.disconnect();
      global.removeEventListener('resize', schedule);
    };
  }

  global.H5ChartTheme = {
    tokens: tokens,
    baseOption: baseOption,
    motionOption: motionOption,
    applyMotion: applyMotion,
    update: update,
    resizeVisible: resizeVisible,
    createResizeObserver: createResizeObserver
  };
})(window);
