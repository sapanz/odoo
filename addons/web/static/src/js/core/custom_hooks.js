odoo.define('web.custom_hooks', function () {
    "use strict";

    const { Component, hooks } = owl;
    const { onMounted, onPatched, onWillUnmount, useState } = hooks;

    /**
     * Focus a given selector as soon as it appears in the DOM and if it was not
     * displayed before. If the selected target is an input|textarea, set the selection
     * at the end.
     * @param {Object} [params]
     * @param {string} [params.selector='autofocus'] default: select the first element
     *                 with an `autofocus` attribute.
     * @returns {Function} function that forces the focus on the next update if visible.
     */
    function useAutofocus(params = {}) {
        const comp = Component.current;
        // Prevent autofocus in mobile
        if (comp.env.device.isMobile) {
            return () => {};
        }
        const selector = params.selector || '[autofocus]';
        let target = null;
        function autofocus() {
            const prevTarget = target;
            target = comp.el.querySelector(selector);
            if (target && target !== prevTarget) {
                target.focus();
                if (['INPUT', 'TEXTAREA'].includes(target.tagName)) {
                    target.selectionStart = target.selectionEnd = target.value.length;
                }
            }
        }
        onMounted(autofocus);
        onPatched(autofocus);

        return function focusOnUpdate() {
            target = null;
        };
    }

    /**
     * The useListener hook offers an alternative to Owl's classical event
     * registration mechanism (with attribute 't-on-eventName' in xml). It is
     * especially useful for abstract components, meant to be extended by
     * specific ones. If those abstract components need to define event handlers,
     * but don't have any template (because the template completely depends on
     * specific cases), then using the 't-on' mechanism isn't adequate, as the
     * handlers would be lost by the template override. In this case, using this
     * hook instead is more convenient.
     *
     * Example: navigation event handling in AbstractField
     *
     * Usage: like all Owl hooks, this function has to be called in the
     * constructor of an Owl component:
     *
     *   useListener('click', () => { console.log('clicked'); });
     *
     * An optional native query selector can be specified as second argument for
     * event delegation. In this case, the handler is only called if the event
     * is triggered on an element matching the given selector.
     *
     *   useListener('click', 'button', () => { console.log('clicked'); });
     *
     * Note: components that alter the event's target (e.g. Portal) are not
     * expected to behave as expected with event delegation.
     *
     * @param {string} eventName the name of the event
     * @param {string} [querySelector] a JS native selector for event delegation
     * @param {function} handler the event handler (will be bound to the component)
     * @param {Object} [addEventListenerOptions] to be passed to addEventListener as options.
     *    Useful for listening in the capture phase
     */
    function useListener(eventName, querySelector, handler, addEventListenerOptions) {
        if (typeof arguments[1] !== 'string') {
            querySelector = null;
            handler = arguments[1];
            addEventListenerOptions = arguments[2];
        }
        if (typeof handler !== 'function') {
            throw new Error('The handler must be a function');
        }

        const comp = Component.current;
        let boundHandler;
        if (querySelector) {
            boundHandler = function (ev) {
                let el = ev.target;
                let target;
                while (el && !target) {
                    if (el.matches(querySelector)) {
                        target = el;
                    } else if (el === comp.el) {
                        el = null;
                    } else {
                        el = el.parentElement;
                    }
                }
                if (el) {
                    handler.call(comp, ev);
                }
            };
        } else {
            boundHandler = handler.bind(comp);
        }
        onMounted(function () {
            comp.el.addEventListener(eventName, boundHandler, addEventListenerOptions);
        });
        onWillUnmount(function () {
            comp.el.removeEventListener(eventName, boundHandler, addEventListenerOptions);
        });
    }

    /**
     * @param {any} initialValue
     * @param {(newValue: any) => any} [processFn] Called to process and return
     *      the new value (can be async).
     * @returns {Object}
     */
    function useSharedValue(initialValue, processFn) {
        // Properties
        let isEditing = false;
        let isLocked = false;
        let value = initialValue;

        // Functions
        let process = processFn || (x => x);
        let render = () => {};

        return {
            /**
             * @returns {Boolean}
             */
            get isEditing() {
                return isEditing;
            },
            /**
             * @returns {Boolean}
             */
            get isLocked() {
                return isLocked;
            },
            /**
             * @returns {any}
             */
            get() {
                return value;
            },
            /**
             * @param {any} value
             */
            set(newValue) {
                value = newValue;
            },
            /**
             * If no function is provided, this method will be a hook to render
             * the current component.
             * @param {() => any} [renderFn]
             */
            setRender(renderFn) {
                if (renderFn) {
                    render = renderFn;
                } else {
                    const state = useState({ rev: 0 });
                    render = () => state.rev++;
                }
            },
            /**
             * @param {boolean} [shouldEdit=!isEditing]
             */
            toggleEdit(shouldEdit = !isEditing) {
                if (shouldEdit !== isEditing) {
                    isEditing = shouldEdit;
                    render();
                }
            },
            /**
             * @param {any} newValue
             * @returns {Promise}
             */
            async update(newValue) {
                if (isLocked) {
                    return;
                }

                isLocked = true;
                isEditing = false;
                render();

                value = await process(newValue);

                isLocked = false;
                render();
            },
        };
    }

    return {
        // Hooks
        useAutofocus,
        useListener,
        useSharedValue,
    };
});
