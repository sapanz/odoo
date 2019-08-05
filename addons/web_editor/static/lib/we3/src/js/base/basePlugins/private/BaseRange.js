(function () {
'use strict';

var WrappedRange = we3.WrappedRange;

var BaseRange = class extends we3.AbstractPlugin {
    constructor () {
        super(...arguments);
        this.dependencies = ['Arch', 'Renderer', 'BaseArch', 'BaseRenderer'];
    }
    willStart () {
        this._focusedNodeID = 1;
        this._range = {
            scID: 1,
            so: 0,
            ecID: 1,
            eo: 0,
            ltr: true,
        };
        return super.willStart();
    }
    blurEditor () {
        this._editorFocused = false;
    }
    focusEditor () {
        this._editorFocused = true;
        this.setRange({
            scID: this._range.scID || 1,
            so: this._range.so || 0,
            ecID: this._range.ecID || 1,
            eo: this._range.eo || 0,
            ltr: true,
        });
    }
    setEditorValue () {
        this._reset();
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Get the currently focused node.
     *
     * @returns {ArchNode}
     */
    getFocusedNode () {
        var BaseArch = this.dependencies.BaseArch;
        return BaseArch.getArchNode(this._focusedNodeID) || BaseArch.root;
    }
    /**
     * Get the current range.
     *
     * @returns {WrappedRange}
     */
    getRange () {
        var Renderer = this.dependencies.Renderer;
        var Arch = this.dependencies.Arch;
        var sc = Renderer.getElement(this._range.scID);
        var ec = this._range.scID === this._range.ecID ? sc : Renderer.getElement(this._range.ecID);
        if (!Arch.getArchNode(this._range.scID)) {
            console.warn('The range is corrupt');
        }
        return new WrappedRange(Arch, Renderer, {
            sc: sc,
            scArch: Arch.getArchNode(this._range.scID),
            scID: this._range.scID,
            so: this._range.so,
            ec: ec,
            ecArch: Arch.getArchNode(this._range.ecID),
            ecID: this._range.ecID,
            eo: this._range.eo,
            ltr: this._range.ltr,
        });
    }
    /**
     * Get the range from the selection in the DOM.
     *
     * @private
     * @returns {WrappedRange}
     */
    getRangeFromDOM () {
        return new WrappedRange(this.dependencies.Arch, this.dependencies.Renderer, {});
    }
    /**
     * Returns a list of all selected leaves in the range.
     *
     * @returns {ArchNode []}
     */
    getSelectedLeaves () {
        return this.getSelectedNodes(node => !node.childNodes || !node.childNodes.length);
    }
    /**
     * Returns a list of all selected nodes in the range.
     * If a predicate function is included, only nodes meeting its
     * conditions will be returned.
     *
     * @param {function} [pred]
     * @returns {ArchNode []}
     */
    getSelectedNodes (pred) {
        return this.getRange().getSelectedNodes(pred);
    }
    /**
     * Return true if the start range is the same point as the end range.
     *
     * @returns {Boolean}
     */
    isCollapsed () {
        return this.getRange().isCollapsed();
    }
    /**
     * Return range points from the from `startID` to `endID`.
     *
     * @param {ArchNode|number} start the ArchNode or its ID
     * @param {ArchNode|number} end the ArchNode or its ID
     * @returns {object} {scID: {Number}, so: {Number}, ecID: {Number}, eo: {Number}}
     */
    rangeOn (start, end) {
        var BaseArch = this.dependencies.BaseArch;
        var scArch = typeof start === 'number' ? BaseArch.getArchNode(start) : start;
        var ecArch = typeof end === 'number' ? BaseArch.getArchNode(end) : end;
        return {
            scID: scArch.id,
            so: scArch.isVirtual() ? 1 : 0, // if virtual, move after it
            ecID: ecArch.id,
            eo: ecArch.isVirtual() ? 1 : ecArch.length(), // if virtual, move after it
        };
    }
    /**
     * Restore the range to its last saved value.
     *
     * @returns {Object|undefined} {range: {WrappedRange}, focus: {ArchNode}}
     */
    restore () {
        return this._setRange(this.getRangeFromDOM());
    }
    /**
     * Select all the contents of the previous start container's first
     * unbreakable ancestor
     */
    selectAll () {
        var scArch = this.dependencies.BaseArch.getArchNode(this._range.scID);
        this.setRange({
            scID: scArch.ancestor('isUnbreakable').id,
        });
    }
    /**
     * Set the range and apply it.
     * Pass only `points.scID` to set the range on the whole element.
     * Pass only `points.scID` and `points.so` to collapse the range on the start.
     *
     * @param {Object} points
     * @param {Node} points.scID start arch node id
     * @param {Number} [points.so] start offset
     * @param {Node} [points.ecID] end arch node id
     * @param {Number} [points.eo] must be given if ecID is given
     * @param {Boolean} [points.ltr] true if the selection was made from left to right (from sc to ec)
     * @param {Object} [options]
     * @param {Boolean} [options.moveLeft] true if a movement is initiated from right to left
     * @param {Boolean} [options.moveRight] true if a movement is initiated from left to right
     * @param {Boolean} [options.muteTrigger]
     * @param {Boolean} [options.muteDOMRange]
     * @returns {Object|undefined} {range: {WrappedRange}, focus: {ArchNode}}
     */
    setRange (points, options) {
        this._computeSetRange(points, options);
        return this._setRange(this.getRangeFromDOM(), options);
    }
    /**
     * Return a deep copy of the range values.
     *
     * @returns {Object}
     */
    toJSON () {
        return Object.assign({}, this._range);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Compute and set the range.
     * Pass only `startPoints.scID` to set the range on the whole element.
     * Pass only `startPoints.scID` and `startPoints.so` to collapse the range on the start.
     *
     * @private
     * @param {Object} startPoints
     * @param {Node} startPoints.scID
     * @param {Number} [startPoints.so]
     * @param {Node} [startPoints.ecID]
     * @param {Number} [startPoints.eo] must be given if ecID is given
     * @param {Boolean} [startPoints.ltr] true if the selection was made from left to right (from sc to ec)
     * @param {Object} [options]
     * @param {Boolean} [options.moveLeft] true if a movement is initiated from right to left
     * @param {Boolean} [options.moveRight] true if a movement is initiated from left to right
     */
    _computeSetRange (startPoints, options) {
        var ltr = typeof startPoints.ltr === 'undefined' ? true : startPoints.ltr;
        options = options || {};
        var points = this._deducePoints(startPoints);
        var isCollapsed = points.scID === points.ecID && points.so === points.eo;
        if (options.moveLeft || options.moveRight) {
            points = this._jumpOverVirtualText(points, options);
        }
        points = this._moveToDeepest(points);
        points = this._moveOutOfNotEditable(points);
        points = this._moveOutOfUnbreakable(points, ltr);
        points = this._moveToDeepest(points);
        points = this._moveUpToVoidoid(points, options);
        points = this._moveToEndOfInline(points);
        points = this._moveToBeforeInline(points);
        if (!options.moveLeft && !options.moveRight) {
            points = this._moveToEdgeOfBRSequence(points);
        }
        if ((options.moveLeft || options.moveRight)) {
            var wasCollapsed = this.isCollapsed();
            var doReverseSelection = !ltr && !wasCollapsed;
            points = this._moveToSideOfVoidoid(points, !!options.moveLeft, isCollapsed, doReverseSelection);
        }

        this._didRangeChange = this._willRangeChange(points) || this._didRangeChange;
        var focusedNodeID = this._getFutureFocusNode(points);

        if (this._focusedNodeID !== focusedNodeID) {
            this._didChangeFocusNode = true;
            this._focusedNodeID = focusedNodeID;
        }

        this._range.scID = points.scID;
        this._range.so = points.so;
        this._range.ecID = points.ecID;
        this._range.eo = points.eo;
        this._range.ltr = ltr;
    }
    /**
     * Deduce the intended ids and offsets from the given ids and offsets.
     * Pass only `points.scID` to get the whole element.
     * Pass only `points.scID` and `points.so` to collapse on the start node.
     * Pass only `points.scID` and `points.ecID` to select from start of sc to end of ec
     *
     * @private
     * @param {Object} pointsWithIDs
     * @param {Number} pointsWithIDs.scID
     * @param {Number} [pointsWithIDs.so]
     * @param {Number} [pointsWithIDs.ecID]
     * @param {Number} [pointsWithIDs.eo]
     * @returns {Object}
     */
    _deducePoints (pointsWithIDs) {
        var BaseArch = this.dependencies.BaseArch;
        if (!pointsWithIDs.sc && !pointsWithIDs.scID) {
            return this._deducePoints({
                scID: 1,
                so: 1,
            });
        }
        var scID = pointsWithIDs.scID;
        var so = pointsWithIDs.so || 0;
        var ecID = pointsWithIDs.ecID || scID;
        var eo = pointsWithIDs.eo;
        if (!pointsWithIDs.ecID) {
            eo = typeof pointsWithIDs.so === 'number' ? so : BaseArch.getArchNode(scID).length();
        }
        if (!eo && eo !== 0) {
            eo = BaseArch.getArchNode(ecID).length();
        }
        return {
            scID: scID,
            so: so,
            ecID: ecID,
            eo: eo,
        };
    }
    /**
     * Return the id of what will be the focus node after setting
     * the range to the given points will change the focus node.
     *
     * @private
     * @param {Object} points
     * @param {Number} points.scID
     * @param {Number} points.so
     * @param {Number} points.ecID
     * @param {Number} points.eo
     * @returns {Integer}
     */
    _getFutureFocusNode (points) {
        var start = this._targetedNode(points.scID, points.so);
        var end = this._targetedNode(points.ecID, points.eo);

        if (start === end) {
            return start.id;
        } else if (points.scID === points.ecID && points.so === points.eo - 1) {
            return start.id;
        } else if ((!points.eo || end.id !== points.ecID) && start.isVoidoid() && start === end.previousSibling()) {
            return start.id;
        } else {
            return (start.commonAncestor(end) || start).id;
        }
    }
    /**
     * Return true if the saved range is collapsed.
     *
     * @todo check if public isCollapsed would suffice
     * @private
     * @returns {Boolean}
     */
    _isCollapsed () {
        return this._range.scID === this._range.ecID && this._range.so === this._range.eo;
    }
    /**
     * When pressing the left or right arrow, jump over virtual text nodes.
     *
     * @private
     * @param {Object} points
     * @param {Number} points.scID
     * @param {Number} points.so
     * @param {Number} points.ecID
     * @param {Number} points.eo
     * @param {Object} [options]
     * @param {Boolean} [options.moveLeft] true if a movement is initiated from right to left
     * @param {Boolean} [options.moveRight] true if a movement is initiated from left to right
     * @returns {Object}
     */
    _jumpOverVirtualText (points, options) {
        var oldStart = this.dependencies.BaseArch.getArchNode(this._range.scID);
        var start = this.dependencies.BaseArch.getArchNode(points.scID);
        var oldEnd = this.dependencies.BaseArch.getArchNode(this._range.ecID);
        var end = this.dependencies.BaseArch.getArchNode(points.ecID);
        var isCollapsed = points.scID === points.ecID && points.so === points.eo;
        var prev;
        if (start.id === end.id && start.type === 'TEXT-VIRTUAL') {
            points.eo = points.so;
        }
        // range start is on a virtual node or it already moved from one
        if (options.moveLeft && (start.type === 'TEXT-VIRTUAL' || oldStart.type === 'TEXT-VIRTUAL' && !points.so)) {
            prev = start.prevUntil(a => a.type !== 'TEXT-VIRTUAL', {doCrossUnbreakables: true, doNotInsertVirtual: true});
            if (prev) {
                points.scID = prev.id;
                points.so = prev.length();
                if (!isCollapsed && points.so) {
                    points.so = points.so - 1; // otherwise it selects the virtual
                }
            }
        } else if (options.moveLeft && oldStart.type === 'TEXT-VIRTUAL' && points.so > 0) {
            // range moved from a virtual and is not at the start of prev
            points.so = points.so - 1;
        } else if (!isCollapsed && options.moveLeft && (end.type === 'TEXT-VIRTUAL' || oldEnd.type === 'TEXT-VIRTUAL' && points.eo === end.length())) {
            // deselect a virtual node to the left (on end)
            prev = end.prevUntil(a => a.type !== 'TEXT-VIRTUAL', {doCrossUnbreakables: true, doNotInsertVirtual: true});
            if (prev) {
                points.ecID = prev.id;
                points.eo = prev.length();
            }
        }
        var next;
        // range end is on a virtual node or it already moved from one
        if (options.moveRight && (end.type === 'TEXT-VIRTUAL' || oldEnd.type === 'TEXT-VIRTUAL' && points.eo === end.length())) {
            next = end.nextUntil(a => a.type !== 'TEXT-VIRTUAL', {doCrossUnbreakables: true, doNotInsertVirtual: true});
            if (next) {
                points.ecID = next.id;
                points.eo = next.isText() && end.type === 'TEXT-VIRTUAL' ? 1 : 0;
            }
        } else if (options.moveRight && oldEnd.type === 'TEXT-VIRTUAL' && points.eo < end.length()) {
            // range moved from a virtual and is not at the end of next
            points.eo = points.eo + 1;
        } else if (!isCollapsed && options.moveRight && (start.type === 'TEXT-VIRTUAL' || oldStart.type === 'TEXT-VIRTUAL' && !points.so)) {
            next = start.nextUntil(a => a.type !== 'TEXT-VIRTUAL', {doCrossUnbreakables: true, doNotInsertVirtual: true});
            if (next) {
                points.scID = next.id;
                points.so = next.isText() && end.type === 'TEXT-VIRTUAL' ? 1 : 0;
            }
        }
        if (isCollapsed) {
            if (options.moveLeft) {
                points.ecID = points.scID;
                points.eo = points.so;
            } else if (options.moveRight) {
                points.scID = points.ecID;
                points.so = points.eo;
            }
        }
        return points;
    }
    /**
     * Move the points out of not-editable nodes.
     *
     * @private
     * @param {Object} points
     * @param {Number} points.scID
     * @param {Number} points.so
     * @param {Number} points.ecID
     * @param {Number} points.eo
     * @returns {Object}
     */
    _moveOutOfNotEditable (points) {
        var self = this;
        var startPoint = __moveOutOfNotEditable(points.scID, points.so, true) || __moveOutOfNotEditable(points.scID, points.so, false);
        var endPoint = __moveOutOfNotEditable(points.ecID, points.eo, false) || __moveOutOfNotEditable(points.scID, points.so, true);
        function __moveOutOfNotEditable(id, offset, ltr) {
            var archNode = self.dependencies.BaseArch.getArchNode(id);
            while (archNode && !archNode.isRoot() && !archNode.isEditable()) {
                archNode = archNode[ltr ? 'next' : 'prev']({
                    doNotInsertVirtual: true,
                    doCrossUnbreakables: true,
            });
                offset = ltr || !archNode ? 0 : archNode.length();
            }
            return archNode && !archNode.isRoot() ? {
                id: archNode.id,
                offset: offset,
            } : null;
        }
        return {
            scID: startPoint ? startPoint.id : 1,
            so: startPoint ? startPoint.offset : 0,
            ecID: endPoint ? endPoint.id : 1,
            eo: endPoint ? endPoint.offset : 0,
        };
    }
    /**
     * Move the points out of unbreakable nodes.
     * A selection cannot cross the bounds of an unbreakable node.
     * This brings back the end of the selection to the first point that doesn't
     * cross these bounds (respecting the direction of the selection).
     *
     * @private
     * @param {Object} points
     * @param {Number} points.scID
     * @param {Number} points.so
     * @param {Number} points.ecID
     * @param {Number} points.eo
     * @param {Boolean} ltr true if the selection was made from left to right (from sc to ec)
     * @returns {Object}
     */
    _moveOutOfUnbreakable (points, ltr) {
        var start = this.dependencies.BaseArch.getArchNode(ltr ? points.scID : points.ecID);
        var end = this.dependencies.BaseArch.getArchNode(ltr ? points.ecID : points.scID);
        var unbreakableAncestorOf = function (node) {
            return node.ancestor(function (ancestor) {
                return ancestor.isUnbreakable() && ancestor.isNotVoidoid();
            });
        };
        var startUnbreakable = unbreakableAncestorOf(start);
        var endUnbreakable = unbreakableAncestorOf(end);
        var nextOptions = {
            doNotInsertVirtual: true,
            doCrossUnbreakables: true,
        };
        if (startUnbreakable.id !== endUnbreakable.id) {
            var nextPred = function (ref) {
                return function (next) {
                    return (!ref || next.ancestor('isUnbreakable') === ref) &&
                        next.isEditable();
                };
            };
            var prevNext;
            var toStart = !ltr;
            if (endUnbreakable.isVoidoid()) {
                prevNext = ltr ? 'nextUntil' : 'prevUntil';
                end = end[prevNext](nextPred(), nextOptions);
                toStart = ltr;
            } else {
                prevNext = ltr ? 'prevUntil' : 'nextUntil';
                end = end[prevNext](nextPred(startUnbreakable), nextOptions);
            }
            if (end) {
                points[ltr ? 'ecID' : 'scID'] = end.id;
                // selection from left to right -> move end left
                points[ltr ? 'eo' : 'so'] = toStart ? 0 : end.length();
            }
        }
        return points;
    }
    /**
     * Move the points to before an inline node if it's on its left edge.
     * This is used to harmonize the behavior between browsers.
     * Eg: text<b>◆text</b>text -> text◆<b>text</b>text
     *
     * @private
     * @param {Object} points
     * @param {Number} points.scID
     * @param {Number} points.so
     * @param {Number} points.ecID
     * @param {Number} points.eo
     * @returns {Object}
     */
    _moveToBeforeInline (points) {
        var isCollapsed = points.scID === points.ecID && points.so === points.eo;
        var archSC = this.dependencies.BaseArch.getArchNode(points.scID);
        /* This only concerns inline nodes that can have children.
        Also, do not move if we are on a virtual as it means its position is
        intentional (eg: <b>virtual</b> so we can write in bold). */
        if (archSC.isVoidoid() || archSC.isVoid() || archSC.isVirtual()) {
            return points;
        }
        var isLeftEdgeOfInline = !points.so &&
            (archSC.isInlineFormatNode() ||
                archSC.isLeftEdge() && archSC.ancestor('isInlineFormatNode'));
        var prev = archSC.previousSibling();
        if (isCollapsed && isLeftEdgeOfInline && prev) {
            points = this._deducePoints({
                scID: prev.id,
                so: prev.length(),
            });
            points = this._moveToDeepest(points);
        }
        return points;
    }
    /**
     * Move the points to their deepest children.
     *
     * @private
     * @param {Object} points
     * @param {Number} points.scID
     * @param {Number} points.so
     * @param {Number} points.ecID
     * @param {Number} points.eo
     * @returns {Object}
     */
    _moveToDeepest (points) {
        var self = this;
        var startPoint = __moveToDeepest(points.scID, points.so);
        var endPoint = __moveToDeepest(points.ecID, points.eo);
        function __isEdgeVoidoid(node) {
            var isLeftEdge = node.isLeftEdgeOfBlock();
            var isRightEdge = node.isRightEdgeOfBlock();
            return node.isVoidoid() && (isLeftEdge || isRightEdge);
        }
        function __moveToDeepest(id, offset) {
            var archNode = self.dependencies.BaseArch.getArchNode(id);
            if (!archNode) {
                return;
            }
            var previousOffset = offset;
            var newOffset = offset;
            var previousArchNode = archNode;
            while (archNode.childNodes && archNode.childNodes.length && !archNode.isVoidoid()) {
                previousArchNode = archNode;
                previousOffset = newOffset;
                if (!newOffset && archNode.previousSibling() && archNode.previousSibling().isTable()) {
                    archNode = archNode.previousSibling().lastLeaf();
                    newOffset = archNode.length();
                } else {
                    var isAfterEnd = newOffset >= archNode.childNodes.length;
                    archNode = archNode.nthChild(isAfterEnd ? archNode.childNodes.length - 1 : newOffset);
                    newOffset = isAfterEnd ? archNode.length() : 0;
                }
            }
            if (__isEdgeVoidoid(archNode) && !archNode.isBR()) {
                return {
                    id: previousArchNode.id,
                    offset: previousOffset,
                };
            }
            return {
                id: archNode.id,
                offset: newOffset,
            };
        };
        if (!startPoint) {
            startPoint = {
                id: 1,
                offset: 0,
            };
        }
        if (!endPoint) {
            endPoint = startPoint;
        }
        return {
            scID: startPoint.id,
            so: startPoint.offset,
            ecID: endPoint.id,
            eo: endPoint.offset,
        };
    }
    /**
     * If the points are collapsed on a first/last BR of a series of BRs
     * and there is something before/after it, move them to the end/start of that
     * something. This ensures proper positioning of the carret in the browser.
     *
     * @private
     * @param {Object} points
     * @param {Number} points.scID
     * @param {Number} points.so
     * @param {Number} points.ecID
     * @param {Number} points.eo
     * @returns {Object}
     */
    _moveToEdgeOfBRSequence (points) {
        var archNode = this.dependencies.BaseArch.getArchNode(points.scID);
        var isCollapsed = points.scID === points.ecID && points.so === points.eo;
        if (!isCollapsed || !archNode.isBR()) {
            return points;
        }
        var prev = archNode.previousSibling();
        var next = archNode.nextSibling();
        if (!prev || !next) {
            return points;
        }
        var isLeftEdge = !prev.isBR() && next.isBR();
        var isRightEdge = prev.isBR() && !next.isBR();
        if (isRightEdge || isLeftEdge || prev.isText() && next.isText()) {
            return {
                scID: isLeftEdge ? prev.id : next.id,
                so: isLeftEdge ? prev.length() : 0,
                ecID: isLeftEdge ? prev.id : next.id,
                eo: isLeftEdge ? prev.length() : 0,
            };
        }
        return points;
    }
    /**
     * Move the points to within an inline node if it's on its right edge.
     * This is used to harmonize the behavior between browsers.
     * Eg: text<b>text</b>◆text -> text<b>text◆</b>text
     *
     * @param {Object} points
     * @param {Number} points.scID
     * @param {Number} points.so
     * @param {Number} points.ecID
     * @param {Number} points.eo
     * @returns {Object}
     */
    _moveToEndOfInline (points) {
        var isCollapsed = points.scID === points.ecID && points.so === points.eo;
        var archSC = this.dependencies.BaseArch.getArchNode(points.scID);
        /* This only concerns inline nodes that can have children.
        Also, do not move if we are on a virtual as it means its position is
        intentional (eg: <b>virtual</b> so we can write in bold). */
        if (archSC.isVoidoid() || archSC.isVoid() || archSC.isVirtual()) {
            return points;
        }
        var prev = archSC.previousSibling();
        var prevIsInline = prev && prev.isInlineFormatNode();
        if (isCollapsed && !points.so && prevIsInline) {
            points = this._deducePoints({
                scID: prev.id,
                so: prev.length(),
            });
            points = this._moveToDeepest(points);
        }
        return points;
    }
    /**
     * Move the points from in a voidoid to the specified side of it, if the
     * voidoid is on the edge of its unbreakable container.
     *
     * @param {Object} points
     * @param {Number} points.scID
     * @param {Number} points.so
     * @param {Number} points.ecID
     * @param {Number} points.eo
     * @param {boolean} [moveLeft] true to move to the left
     * @param {boolean} [isCollapsed] true if the range started collapsed
     * @param {boolean} [doReverseSelection] true to reverse the selection
     * @returns {Object}
     */
    _moveToSideOfEdgeVoidoid (points, moveLeft, isCollapsed, doReverseSelection) {
        var scArch = this.dependencies.BaseArch.getArchNode(points.scID);
        var ecArch = this.dependencies.BaseArch.getArchNode(points.ecID);
        var left = doReverseSelection ? ecArch : scArch;
        var right = doReverseSelection ? scArch : ecArch;
        if (moveLeft && !left.isVoidoid()) {
            return points;
        }
        if (!moveLeft && !right.isVoidoid()) {
            return points;
        }
        var node = moveLeft ? left.parent : right.parent;
        if (isCollapsed) {
            points.so = points.eo = moveLeft ? 0 : node.length();
            points.scID = points.ecID = node.id;
        } else if (moveLeft) {
            points[doReverseSelection ? 'eo' : 'so'] = 0;
            points[doReverseSelection ? 'ecID' : 'scID'] = node.id;
        } else {
            points[doReverseSelection ? 'so' : 'eo'] = node.length();
            points[doReverseSelection ? 'scID' : 'ecID'] = node.id;
        }
        return points;
    }
    /**
     * Move the points from in a voidoid to the specified side of it, if the
     * voidoid is not on the edge of its unbreakable container.
     *
     * @param {Object} points
     * @param {Number} points.scID
     * @param {Number} points.so
     * @param {Number} points.ecID
     * @param {Number} points.eo
     * @param {boolean} [moveLeft] true to move to the left
     * @param {boolean} [isCollapsed] true if the range started collapsed
     * @param {boolean} [doReverseSelection] true to reverse the selection
     * @returns {Object}
     */
    _moveToSideOfMiddleVoidoid (points, moveLeft, isCollapsed, doReverseSelection) {
        var scArch = this.dependencies.BaseArch.getArchNode(points.scID);
        var ecArch = this.dependencies.BaseArch.getArchNode(points.ecID);
        var prevOptions = {
            leafToLeaf: true,
            // voidoid is an unbreakable, we need to be able to cross it:
            doCrossUnbreakables: true,
            doNotInsertVirtual: true,
        };

        var prev, next;
        if (doReverseSelection) {
            prev = ecArch.prev(prevOptions);
            next = scArch.next(prevOptions);
            if (isCollapsed) {
                points.so = points.eo = moveLeft ? prev.length() : 0;
                points.scID = points.ecID = moveLeft ? prev.id : next.id;
            } else if (ecArch.isVoidoid()) {
                if (moveLeft) {
                    points.eo = 0;
                    points.ecID = next.id;
                } else {
                    points.so = next.length();
                    points.scID = prev.id;
                }
            }
        } else {
            prev = scArch.prev(prevOptions);
            next = ecArch.next(prevOptions);
            if (isCollapsed) {
                points.so = points.eo = moveLeft ? prev.length() : 0;
                points.scID = points.ecID = moveLeft ? prev.id : next.id;
            } else if (scArch.isVoidoid()) {
                if (moveLeft) {
                    points.so = prev.length();
                    points.scID = prev.id;
                } else {
                    points.eo = 0;
                    points.ecID = next.id;
                }
            }
        }
        return points;
    }
    /**
     * Move the points from in a voidoid to the specified side of it.
     *
     * @param {object} points
     * @param {Number} points.scID
     * @param {Number} points.so
     * @param {Number} points.ecID
     * @param {Number} points.eo
     * @param {boolean} [moveLeft] true to move to the left
     * @param {boolean} [isCollapsed] true if the range started collapsed
     * @param {boolean} [doReverseSelection] true to reverse the selection
     * @returns {object}
     */
    _moveToSideOfVoidoid (points, moveLeft, isCollapsed, doReverseSelection) {
        var scArch = this.dependencies.BaseArch.getArchNode(points.scID);
        var ecArch = this.dependencies.BaseArch.getArchNode(points.ecID);
        if ((!scArch.isVoidoid() || scArch.isBR()) && (!ecArch.isVoidoid() || ecArch.isBR())) {
            return points;
        }

        var unbreakableAncestorOf = function (node) {
            return node.ancestor(function (ancestor) {
                return (ancestor.isUnbreakable() || ancestor.isBlock()) && ancestor.isNotVoidoid();
            });
        };
        var left = doReverseSelection ? ecArch : scArch;
        var right = doReverseSelection ? scArch : ecArch;
        var isLeftEdge = left.isLeftEdgeOf(unbreakableAncestorOf(left));
        var isRightEdge = right.isRightEdgeOf(unbreakableAncestorOf(right));

        if (isLeftEdge && moveLeft || isRightEdge && !moveLeft) {
            points = this._moveToSideOfEdgeVoidoid(points, moveLeft, isCollapsed, doReverseSelection);
        } else if (!isLeftEdge && !isRightEdge) {
            points = this._moveToSideOfMiddleVoidoid(points, moveLeft, isCollapsed, doReverseSelection);
        }
        return points;
    }
    /**
     * Move the points from WITHIN a voidoid to select the whole voidoid instead if needed.
     *
     * @private
     * @param {Object} points
     * @param {Number} points.scID
     * @param {Number} points.so
     * @param {Number} points.ecID
     * @param {Number} points.eo
     * @returns {Object}
     */
    _moveUpToVoidoid (points, options) {
        var self = this;
        var moveRight = options.moveRight;
        var isCollapsed = points.scID === points.ecID && points.so === points.eo;
        var startPoint = __moveUpToVoidoid(points.scID, points.so, isCollapsed, true);
        var endPoint = !isCollapsed && __moveUpToVoidoid(points.ecID, points.eo, isCollapsed, moveRight) || startPoint;
        function __moveUpToVoidoid(id, offset, isCollapsed, isStart) {
            var archNode = self.dependencies.BaseArch.getArchNode(id);
            var voidoidAncestor = archNode.ancestor('isVoidoid', true);
            if (voidoidAncestor && !voidoidAncestor.isVoid()) {
                id = voidoidAncestor.id;
                offset = 0;
                if (!isCollapsed) {
                    archNode = voidoidAncestor.index() && voidoidAncestor[moveRight ? 'nextUntil' : 'prevUntil'](function (archNode) {
                        return archNode.id !== id && (archNode.isUnbreakable() || archNode.isBlock() || archNode.isText() || archNode.isVoidoid());
                    }, {
                        doNotInsertVirtual: true,
                    });
                    if (archNode) {
                        id = archNode.id;
                        offset = moveRight ? 0 : archNode.length();
                    } else {
                        id = voidoidAncestor.parent.id;
                        offset = voidoidAncestor.index() + (moveRight ? 1 : 0);
                    }
                }
            }
            return {
                id: id,
                offset: offset,
            };
        }
        return {
            scID: startPoint ? startPoint.id : 1,
            so: startPoint ? startPoint.offset : 0,
            ecID: endPoint ? endPoint.id : 1,
            eo: endPoint ? endPoint.offset : 0,
        };
    }
    /**
     * Reset the range on the starting point of the editor.
     *
     * @private
     */
    _reset () {
        this.setRange({
            scID: 1,
            so: 0,
        });
    }
    /**
     * Set the DOM Range from the given points.
     *
     * @private
     * @param {Node} sc
     * @param {Number} so
     * @param {Node} ec
     * @param {Number} eo
     * @param {Boolean} [rtl]
     */
    _select (sc, so, ec, eo, rtl) {
        if (this.editable.style.display === 'none') {
            return;
        }
        if (this.editable !== document.activeElement) {
            this.editable.focus();
        }
        var nativeRange = this._toNativeRange(sc, so, ec, eo);
        var selection = sc.ownerDocument.getSelection();
        if (selection.rangeCount > 0) {
            selection.removeAllRanges();
        }
        if (!this.document.body.contains(sc)) {
            console.warn("The given range isn't in document.");
            return;
        }
        if (rtl) {
            // select in the rtl direction
            nativeRange.setStart(ec, eo);
            nativeRange.setEnd(ec, eo);
            selection.removeAllRanges();
            selection.addRange(nativeRange);
            selection = sc.ownerDocument.getSelection();
            selection.extend(sc, so);
        }
        selection.addRange(nativeRange);
    }
    /**
     * Set the range in the DOM.
     *
     * @private
     * @param {Object} [oldRange]
     * @param {Node} [oldRange.sc]
     * @param {Number} [oldRange.scID]
     * @param {Number} [oldRange.so]
     * @param {Node} [oldRange.ec]
     * @param {Number} [oldRange.ecID]
     * @param {Number} [oldRange.eo]
     * @param {Object} [options]
     * @param {Boolean} [options.muteTrigger]
     * @param {Boolean} [options.muteDOMRange]
     * @returns {Object|undefined} {range: {WrappedRange}, focus: {ArchNode}}
     */
    _setRange (oldRange, options) {
        if (!this._editorFocused) {
            return;
        }

        var newRange = this.getRange();
        var nativeReadyNewRange = this._voidoidSelectToNative(newRange);

        if ((!options || !options.muteDOMRange) &&
            (!oldRange || oldRange.scID === 1 ||
            oldRange.sc !== nativeReadyNewRange.sc || oldRange.so !== nativeReadyNewRange.so ||
            oldRange.ec !== nativeReadyNewRange.ec || oldRange.eo !== nativeReadyNewRange.eo)) {
            // only if the native range change, after the redraw
            // the renderer can associate existing note to the arch (to prevent error on mobile)
            try {
                this._select(nativeReadyNewRange.sc, nativeReadyNewRange.so, nativeReadyNewRange.ec, nativeReadyNewRange.eo, !this._range.ltr);
            } catch (e) {
                var msg = 'Wrong Range! The nodes could node be found in the DOM.';
                console.warn(msg + '\nnewRange: ', newRange, '\nnativeRange:', nativeReadyNewRange);
            }
        }

        var didRangeChange = this._didRangeChange;
        var isChangeFocusNode = this._didChangeFocusNode;
        this._didRangeChange = false;
        this._didChangeFocusNode = false;

        var res = {};
        if (didRangeChange) {
            res.range = this.toJSON();
            if (!options || !options.muteTrigger) {
                this.trigger('range', res.range);
            } else {
                // this._didRangeChange = didRangeChange; // TODO: fix undo
            }
        }
        if (isChangeFocusNode) {
            res.focus = this.getFocusedNode();
            if (!options || !options.muteTrigger) {
                this.trigger('focus', res.focus);
            } else {
                this._didChangeFocusNode = isChangeFocusNode;
            }
        }

        return res;
    }
    /**
     * Return the node targeted by the given ArchNode ID and its offset.
     *
     * @private
     * @param {Number} id
     * @param {Number} offset
     * @returns {ArchNode}
     */
    _targetedNode (id, offset) {
        var archNode = this.dependencies.BaseArch.getArchNode(id);
        if (archNode && !archNode.isVoidoid() && archNode.childNodes && archNode.childNodes[offset]) {
            archNode = archNode.childNodes[offset];
        }
        return archNode;
    }
    /**
     * Get the native Range object corresponding to the given range points.
     *
     * @private
     * @param {Node} sc
     * @param {Number} so
     * @param {Node} ec
     * @param {Number} eo
     * @returns {Range}
     */
    _toNativeRange (sc, so, ec, eo) {
        var nativeRange = sc.ownerDocument.createRange();
        nativeRange.setStart(sc, so);
        nativeRange.setEnd(ec, eo);
        return nativeRange;
    }
    /**
     * Convert a range to ensure compatibility with native range,
     * with regards to voidoid selection.
     * In we3, a selected voidoid is within the voidoid.
     * For a native range, we need to select the voidoid from within its parent.
     *
     * @private
     * @param {object} range
     * @param {Node} range.sc
     * @param {number} range.so
     * @param {Node} range.ec
     * @param {number} range.eo
     * @returns {object} {sc, so, ec, eo}
     */
    _voidoidSelectToNative (range) {
        var sc = range.sc;
        var so = range.so;
        if (range.scArch.isVoidoid() && sc && sc.parentNode) {
            so = [].indexOf.call(sc.parentNode.childNodes, sc);
            sc = sc.parentNode;
        }
        var ec = range.ec;
        var eo = range.eo;
        if (range.ecArch.isVoidoid() && ec && ec.parentNode) {
            eo = [].indexOf.call(ec.parentNode.childNodes, ec) + (range.ecArch.isBR() ? 0 : 1);
            ec = ec.parentNode;
        }
        return {
            sc: sc,
            so: so,
            ec: ec,
            eo: eo,
        };
    }
    /**
     * Return true if the range will change once set to the given points.
     *
     * @private
     * @param {Object} points
     * @param {Number} points.scID
     * @param {Number} points.so
     * @param {Number} points.ecID
     * @param {Number} points.eo
     * @returns {Boolean}
     */
    _willRangeChange (points) {
        var willOffsetChange = points.so !== this._range.so || points.eo !== this._range.eo;
        var willIDsChange = points.scID !== this._range.scID || points.ecID !== this._range.ecID;
        var willNodesChange = this.dependencies.BaseRenderer.getElement(points.scID) !== this.dependencies.BaseRenderer.getElement(this._range.scID) ||
            this.dependencies.BaseRenderer.getElement(points.ecID) !== this.dependencies.BaseRenderer.getElement(this._range.ecID);
        return willOffsetChange || willIDsChange || willNodesChange;
    }
};

we3.pluginsRegistry.BaseRange = BaseRange;

})();
