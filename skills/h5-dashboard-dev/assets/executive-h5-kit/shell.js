/* Executive H5 Kit · accessible tabs and drawer, no dependency. */
(function (global) {
  'use strict';

  var focusableSelector = [
    'a[href]', 'button:not([disabled])', 'input:not([disabled])',
    'select:not([disabled])', 'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])'
  ].join(',');

  function initTabs(root, options) {
    if (!root) throw new Error('initTabs: root is required');
    options = options || {};
    var tabs = Array.prototype.slice.call(root.querySelectorAll('[role="tab"][aria-controls]'));
    if (!tabs.length) throw new Error('initTabs: no tabs with aria-controls');
    var automatic = options.activation ? options.activation === 'auto' : root.dataset.activation === 'auto';

    function panelFor(tab) { return document.getElementById(tab.getAttribute('aria-controls')); }
    function selected() { return root.querySelector('[role="tab"][aria-selected="true"]') || tabs[0]; }

    function activate(tabOrId, config) {
      config = config || {};
      var tab = typeof tabOrId === 'string' ? document.getElementById(tabOrId) : tabOrId;
      if (!tab || tabs.indexOf(tab) < 0 || tab.disabled) return false;
      var panel = panelFor(tab);
      if (!panel) return false;
      var previous = selected();
      tabs.forEach(function (item) {
        var active = item === tab;
        item.setAttribute('aria-selected', String(active));
        item.tabIndex = active ? 0 : -1;
        var target = panelFor(item);
        if (target) {
          target.hidden = !active;
          target.setAttribute('aria-hidden', String(!active));
        }
      });
      if (config.focus) tab.focus();
      if (config.emit !== false) {
        root.dispatchEvent(new CustomEvent('h5:tabchange', {
          bubbles: true,
          detail: {
            id: tab.id,
            panelId: panel.id,
            previousId: previous && previous !== tab ? previous.id : null,
            tab: tab,
            panel: panel
          }
        }));
      }
      return true;
    }

    function onClick(event) {
      var tab = event.target.closest('[role="tab"]');
      if (tab && tabs.indexOf(tab) >= 0) activate(tab);
    }

    function onKeydown(event) {
      var tab = event.target.closest('[role="tab"]');
      if (!tab || tabs.indexOf(tab) < 0) return;
      var vertical = root.getAttribute('aria-orientation') === 'vertical';
      var previousKey = vertical ? 'ArrowUp' : 'ArrowLeft';
      var nextKey = vertical ? 'ArrowDown' : 'ArrowRight';
      var index = tabs.indexOf(tab);
      var target = null;
      if (event.key === previousKey) target = tabs[(index - 1 + tabs.length) % tabs.length];
      if (event.key === nextKey) target = tabs[(index + 1) % tabs.length];
      if (event.key === 'Home') target = tabs[0];
      if (event.key === 'End') target = tabs[tabs.length - 1];
      if (target) {
        event.preventDefault();
        target.focus();
        if (automatic) activate(target);
        return;
      }
      if (!automatic && (event.key === 'Enter' || event.key === ' ')) {
        event.preventDefault();
        activate(tab);
      }
    }

    root.addEventListener('click', onClick);
    root.addEventListener('keydown', onKeydown);
    activate(selected(), { emit: false });

    return {
      activate: activate,
      getSelected: selected,
      destroy: function () {
        root.removeEventListener('click', onClick);
        root.removeEventListener('keydown', onKeydown);
      }
    };
  }

  function initDrawer(options) {
    options = options || {};
    var drawer = options.drawer;
    var scrim = options.scrim;
    var trigger = options.trigger;
    if (!drawer) throw new Error('initDrawer: drawer is required');
    var modal = options.modal !== false;
    var background = Array.isArray(options.background) ? options.background.filter(Boolean) : [];
    var backgroundState = [];
    var opener = null;
    var isOpen = false;

    function focusables() {
      return Array.prototype.slice.call(drawer.querySelectorAll(focusableSelector)).filter(function (el) {
        return !el.hidden && el.getAttribute('aria-hidden') !== 'true' && el.getClientRects().length;
      });
    }

    function open(triggerOverride) {
      if (isOpen) return;
      isOpen = true;
      opener = triggerOverride || trigger || document.activeElement;
      drawer.hidden = false;
      if (scrim) scrim.hidden = false;
      document.body.classList.add('h5-drawer-open');
      if (trigger) trigger.setAttribute('aria-expanded', 'true');
      if (modal) {
        drawer.setAttribute('aria-modal', 'true');
        backgroundState = background.map(function (el) { return { el: el, inert: !!el.inert }; });
        background.forEach(function (el) { el.inert = true; });
      }
      var first = drawer.querySelector('[autofocus]') || focusables()[0] || drawer;
      if (first === drawer && !drawer.hasAttribute('tabindex')) drawer.tabIndex = -1;
      first.focus();
      drawer.dispatchEvent(new CustomEvent('h5:drawerchange', { bubbles: true, detail: { open: true } }));
    }

    function close(config) {
      if (!isOpen) return;
      config = config || {};
      isOpen = false;
      drawer.hidden = true;
      if (scrim) scrim.hidden = true;
      document.body.classList.remove('h5-drawer-open');
      if (trigger) trigger.setAttribute('aria-expanded', 'false');
      backgroundState.forEach(function (item) { item.el.inert = item.inert; });
      backgroundState = [];
      if (config.restoreFocus !== false && opener && opener.isConnected) opener.focus();
      drawer.dispatchEvent(new CustomEvent('h5:drawerchange', { bubbles: true, detail: { open: false } }));
    }

    function onKeydown(event) {
      if (!isOpen) return;
      if (event.key === 'Escape') {
        event.preventDefault();
        close();
        return;
      }
      if (!modal || event.key !== 'Tab') return;
      var items = focusables();
      if (!items.length) {
        event.preventDefault();
        drawer.focus();
        return;
      }
      var first = items[0];
      var last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    function onTrigger() { if (isOpen) close(); else open(); }
    function onCloseClick(event) {
      var button = event.target.closest('[data-h5-close]');
      if (button && drawer.contains(button)) close();
    }

    if (trigger) {
      trigger.setAttribute('aria-expanded', 'false');
      if (!trigger.hasAttribute('aria-controls')) trigger.setAttribute('aria-controls', drawer.id);
      trigger.addEventListener('click', onTrigger);
    }
    drawer.addEventListener('keydown', onKeydown);
    drawer.addEventListener('click', onCloseClick);
    if (scrim) scrim.addEventListener('click', close);

    return {
      open: open,
      close: close,
      isOpen: function () { return isOpen; },
      destroy: function () {
        if (trigger) trigger.removeEventListener('click', onTrigger);
        drawer.removeEventListener('keydown', onKeydown);
        drawer.removeEventListener('click', onCloseClick);
        if (scrim) scrim.removeEventListener('click', close);
      }
    };
  }

  global.H5Shell = { initTabs: initTabs, initDrawer: initDrawer };
})(window);
