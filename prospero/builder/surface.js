export default {
  template: `
    <div ref="shell" class="studio-surface" :style="{width: width * scale + 'px', height: height * scale + 'px'}">
      <div ref="screen" class="studio-screen" :style="{width: width + 'px', transform: 'scale(' + scale + ')'}"><slot></slot></div>
      <div v-if="editing" class="studio-hit-layer" tabindex="0" role="application" aria-label="Screen canvas"
        draggable="true" @click="selectAt" @dblclick="focusProperties" @dragstart="startDrag"
        @dragover.prevent="dragOver" @dragleave="dropMark = null" @drop.prevent="drop" @dragend="dropMark = null"
        @mousemove="hoverAt" @mouseleave="hover = null"></div>
      <div v-if="editing && hover && hover.id !== selected" class="studio-hover-box" :style="hover.style"></div>
      <div v-if="editing && selection" class="studio-selection-box" :style="selection.style">
        <span class="studio-selection-label">{{selection.name}} <small>{{selection.size}}</small></span>
        <i class="studio-handle top-left"></i><i class="studio-handle bottom-right"></i>
      </div>
      <div v-if="editing && dropMark" class="studio-drop-mark" :class="{'is-line': dropMark.line}" :style="dropMark.style">
        <span>{{dropMark.label}}</span>
      </div>
    </div>`,
  props: {selected: String, width: Number, zoom: String, editing: Boolean, dirty: Boolean},
  emits: ['select', 'drop-node', 'command', 'focus-properties', 'scale'],
  data() { return {scale: 1, height: 0, selection: null, hover: null, dropMark: null}; },
  mounted() {
    this.queueMeasure = () => { cancelAnimationFrame(this.frame); this.frame = requestAnimationFrame(() => this.measure()); };
    this.resize = new ResizeObserver(this.queueMeasure);
    this.resize.observe(this.$refs.screen);
    this.resize.observe(this.$el.parentElement);
    this.mutations = new MutationObserver(this.queueMeasure);
    this.mutations.observe(this.$refs.screen, {childList: true, subtree: true, attributes: true, characterData: true});
    this.keyListener = event => this.key(event);
    this.unloadListener = event => { if (this.dirty) { event.preventDefault(); event.returnValue = ''; } };
    document.addEventListener('keydown', this.keyListener);
    window.addEventListener('beforeunload', this.unloadListener);
    this.queueMeasure();
  },
  beforeUnmount() {
    this.resize.disconnect(); this.mutations.disconnect(); cancelAnimationFrame(this.frame);
    document.removeEventListener('keydown', this.keyListener);
    window.removeEventListener('beforeunload', this.unloadListener);
  },
  watch: {
    selected() { this.queueMeasure(); }, width() { this.$nextTick(this.queueMeasure); },
    zoom() { this.queueMeasure(); }, editing() { this.hover = null; this.dropMark = null; this.queueMeasure(); }
  },
  methods: {
    nodes() { return [...this.$refs.screen.querySelectorAll('[data-screen-id]')]; },
    byId(id) { return this.nodes().find(el => el.dataset.screenId === id); },
    rect(el) {
      const r = el.getBoundingClientRect(), origin = this.$refs.shell.getBoundingClientRect();
      return {left: (r.left-origin.left)+'px', top: (r.top-origin.top)+'px', width: r.width+'px', height: r.height+'px'};
    },
    info(el) {
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return {id: el.dataset.screenId, name: el.dataset.screenName, style: this.rect(el),
        size: Math.round(r.width / this.scale) + ' × ' + Math.round(r.height / this.scale)};
    },
    measure() {
      const available = this.$el.parentElement.clientWidth - 64;
      const scale = this.zoom === 'Fit' ? Math.min(1, Math.max(0.1, available / this.width)) : Number(this.zoom) / 100;
      if (this.scale !== scale) { this.scale = scale; this.$emit('scale', Math.round(scale * 100)); }
      this.height = this.$refs.screen.offsetHeight;
      this.$nextTick(() => { this.selection = this.info(this.byId(this.selected)); });
    },
    nodeAt(event) {
      return this.nodes().reverse().find(el => {
        const r = el.getBoundingClientRect();
        return r.width > 0 && r.height > 0 && event.clientX >= r.left && event.clientX <= r.right && event.clientY >= r.top && event.clientY <= r.bottom;
      });
    },
    selectAt(event) { const el = this.nodeAt(event); if (el) this.$emit('select', el.dataset.screenId); },
    focusProperties() { this.$emit('focus-properties'); },
    hoverAt(event) { this.hover = this.info(this.nodeAt(event)); },
    startDrag(event) {
      const el = this.nodeAt(event);
      if (!el || !el.dataset.screenParent) { event.preventDefault(); return; }
      event.dataTransfer.setData('application/x-prospero', JSON.stringify({id: el.dataset.screenId}));
      event.dataTransfer.effectAllowed = 'move'; this.$emit('select', el.dataset.screenId);
    },
    dropTarget(event) {
      let target = this.nodeAt(event) || this.nodes()[0];
      if (!target) return null;
      const containers = ['column', 'row', 'grid', 'card'];
      let parent, index, line = false;
      const bounds = target.getBoundingClientRect();
      const edge = Math.min(10 * this.scale, bounds.height / 4);
      if (!containers.includes(target.dataset.screenKind) ||
          (target.dataset.screenParent && (event.clientY < bounds.top + edge || event.clientY > bounds.bottom - edge))) {
        parent = this.byId(target.dataset.screenParent);
        if (!parent) return null;
        const children = this.nodes().filter(el => el.dataset.screenParent === parent.dataset.screenId);
        const horizontal = ['row', 'grid'].includes(parent.dataset.screenKind);
        const after = horizontal ? event.clientX > bounds.left + bounds.width/2 : event.clientY > bounds.top + bounds.height/2;
        index = children.indexOf(target) + (after ? 1 : 0);
        const style = this.rect(target);
        if (horizontal) { style.left = (parseFloat(style.left) + (after ? bounds.width : 0))+'px'; style.width = '2px'; }
        else { style.top = (parseFloat(style.top) + (after ? bounds.height : 0))+'px'; style.height = '2px'; }
        return {parent: parent.dataset.screenId, index, line: true, style, label: after ? 'Insert after' : 'Insert before'};
      }
      parent = target;
      index = this.nodes().filter(el => el.dataset.screenParent === parent.dataset.screenId).length;
      return {parent: parent.dataset.screenId, index, line, style: this.rect(parent), label: 'Add to ' + parent.dataset.screenName};
    },
    dragOver(event) {
      if (!this.editing || !event.dataTransfer.types.includes('application/x-prospero')) return;
      event.stopPropagation(); this.dropMark = this.dropTarget(event);
      const scroll = this.$el.closest('.studio-stage');
      const r = scroll.getBoundingClientRect();
      if (event.clientY > r.bottom - 40) scroll.scrollTop += 12;
      if (event.clientY < r.top + 40) scroll.scrollTop -= 12;
    },
    drop(event) {
      event.stopPropagation();
      const target = this.dropTarget(event);
      this.dropMark = null;
      if (!target || !this.editing) return;
      try { const payload = JSON.parse(event.dataTransfer.getData('application/x-prospero'));
        this.$emit('drop-node', {...payload, parent: target.parent, index: target.index});
      } catch { /* Ignore external drags. */ }
    },
    key(event) {
      if (document.querySelector('.q-dialog')) return;
      const typing = event.target.closest('input,textarea,select,[contenteditable="true"]');
      const mod = event.ctrlKey || event.metaKey;
      let command = null;
      if (mod && event.key.toLowerCase() === 's') command = 'save';
      else if (!typing && mod && event.key.toLowerCase() === 'z') command = event.shiftKey ? 'redo' : 'undo';
      else if (!typing && mod && event.key.toLowerCase() === 'y') command = 'redo';
      else if (!typing && mod && event.key.toLowerCase() === 'd') command = 'duplicate';
      else if (!typing && ['Delete','Backspace'].includes(event.key)) command = 'delete';
      else if (!typing && event.key === 'Escape') command = 'parent';
      if (command) { event.preventDefault(); if (this.editing || command === 'save') this.$emit('command', command); }
    }
  }
};
