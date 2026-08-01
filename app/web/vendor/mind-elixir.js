const ts = 0, ns = 1, os = 2, pe = {
  name: "Latte",
  type: "light",
  palette: ["#dd7878", "#ea76cb", "#8839ef", "#e64553", "#fe640b", "#df8e1d", "#40a02b", "#209fb5", "#1e66f5", "#7287fd"],
  cssVar: {
    "--node-gap-x": "30px",
    "--node-gap-y": "10px",
    "--main-gap-x": "65px",
    "--main-gap-y": "45px",
    "--root-radius": "30px",
    "--main-radius": "20px",
    "--root-color": "#ffffff",
    "--root-bgcolor": "#4c4f69",
    "--root-border-color": "rgba(0, 0, 0, 0)",
    "--main-border": "",
    // you can customize, it will fallback to 2px solid main-color
    "--main-color": "#444446",
    "--main-bgcolor": "#ffffff",
    "--main-bgcolor-transparent": "rgba(255, 255, 255, 0.8)",
    "--topic-padding": "3px",
    "--color": "#777777",
    "--bgcolor": "#f6f6f6",
    "--selected": "#4dc4ff",
    "--accent-color": "#e64553",
    "--panel-color": "#444446",
    "--panel-bgcolor": "#ffffff",
    "--panel-border-color": "#eaeaea",
    "--map-padding": "50px 80px"
  }
}, ge = {
  name: "Dark",
  type: "dark",
  palette: ["#848FA0", "#748BE9", "#D2F9FE", "#4145A5", "#789AFA", "#706CF4", "#EF987F", "#775DD5", "#FCEECF", "#DA7FBC"],
  cssVar: {
    "--node-gap-x": "30px",
    "--node-gap-y": "10px",
    "--main-gap-x": "65px",
    "--main-gap-y": "45px",
    "--root-radius": "30px",
    "--main-radius": "20px",
    "--root-color": "#ffffff",
    "--root-bgcolor": "#2d3748",
    "--root-border-color": "rgba(255, 255, 255, 0.1)",
    "--main-border": "",
    "--main-color": "#ffffff",
    "--main-bgcolor": "#4c4f69",
    "--main-bgcolor-transparent": "rgba(76, 79, 105, 0.8)",
    "--topic-padding": "3px",
    "--color": "#cccccc",
    "--bgcolor": "#252526",
    "--selected": "#4dc4ff",
    "--accent-color": "#789AFA",
    "--panel-color": "#ffffff",
    "--panel-bgcolor": "#2d3748",
    "--panel-border-color": "#696969",
    "--map-padding": "50px 80px"
  }
};
function de(e) {
  return e.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");
}
const oe = function(e, t) {
  if (t.id === e)
    return t;
  if (t.children && t.children.length) {
    for (let n = 0; n < t.children.length; n++) {
      const o = oe(e, t.children[n]);
      if (o) return o;
    }
    return null;
  } else
    return null;
}, B = (e, t) => {
  if (e.parent = t, e.children)
    for (let n = 0; n < e.children.length; n++)
      B(e.children[n], e);
}, K = (e, t, n) => {
  if (e.expanded = t, e.children)
    if (n === void 0 || n > 0) {
      const o = n !== void 0 ? n - 1 : void 0;
      e.children.forEach((s) => {
        K(s, t, o);
      });
    } else
      e.children.forEach((o) => {
        K(o, !1);
      });
};
function me(e) {
  if (e.id = W(), e.children)
    for (let t = 0; t < e.children.length; t++)
      me(e.children[t]);
}
function se(e, t, n, o) {
  const s = n - e, i = o - t, c = Math.atan2(i, s) * 180 / Math.PI, r = 12, a = 30, d = (c + 180 - a) * Math.PI / 180, h = (c + 180 + a) * Math.PI / 180;
  return {
    x1: n + Math.cos(d) * r,
    y1: o + Math.sin(d) * r,
    x2: n + Math.cos(h) * r,
    y2: o + Math.sin(h) * r
  };
}
function W() {
  return ((/* @__PURE__ */ new Date()).getTime().toString(16) + Math.random().toString(16).substring(2)).substring(2, 18);
}
const yt = function() {
  const e = W();
  return {
    topic: this.newTopicName,
    id: e
  };
};
function ie(e) {
  return JSON.parse(
    JSON.stringify(e, (n, o) => {
      if (n !== "parent")
        return o;
    })
  );
}
const A = (e, t) => {
  let n = 0, o = 0;
  for (; t && t !== e; )
    n += t.offsetLeft, o += t.offsetTop, t = t.offsetParent;
  return { offsetLeft: n, offsetTop: o };
}, k = (e, t) => {
  for (const n in t)
    e.setAttribute(n, t[n]);
}, ne = (e) => e ? e.tagName === "ME-TPC" : !1, ye = (e) => e.filter((t) => t.nodeObj.parent).filter((t, n, o) => {
  for (let s = 0; s < o.length; s++) {
    if (t === o[s]) continue;
    const { parent: i } = t.nodeObj;
    if (i === o[s].nodeObj)
      return !1;
  }
  return !0;
}), be = (e) => {
  const t = /translate3d\(([^,]+),\s*([^,]+)/, n = e.match(t);
  return n ? { x: parseFloat(n[1]), y: parseFloat(n[2]) } : { x: 0, y: 0 };
}, qe = function(e) {
  for (let t = 0; t < e.length; t++) {
    const { dom: n, evt: o, func: s } = e[t];
    n.addEventListener(o, s);
  }
  return function() {
    for (let n = 0; n < e.length; n++) {
      const { dom: o, evt: s, func: i } = e[n];
      o.removeEventListener(s, i);
    }
  };
}, Le = (e, t) => {
  const n = e.x - t.x, o = e.y - t.y;
  return Math.sqrt(n * n + o * o);
}, bt = function(e, t) {
  if (!t)
    return re(e), e;
  let n = e.querySelector(".insert-preview");
  const o = `insert-preview ${t} show`;
  return n || (n = document.createElement("div"), e.appendChild(n)), n.className = o, e;
}, re = function(e) {
  if (!e) return;
  const t = e.querySelectorAll(".insert-preview");
  for (const n of t || [])
    n.remove();
}, Ae = function(e, t) {
  for (const n of t) {
    const o = n.parentElement.parentElement.contains(e);
    if (!(e && e.tagName === "ME-TPC" && e !== n && !o && e.nodeObj.parent)) return !1;
  }
  return !0;
}, vt = function(e) {
  const t = document.createElement("div");
  return t.className = "mind-elixir-ghost", e.container.appendChild(t), t;
};
class xt {
  mind;
  isMoving = !1;
  interval = null;
  speed = 20;
  constructor(t) {
    this.mind = t;
  }
  move(t, n) {
    this.isMoving || (this.isMoving = !0, this.interval = setInterval(() => {
      this.mind.move(t * this.speed * this.mind.scaleVal, n * this.speed * this.mind.scaleVal);
    }, 100));
  }
  stop() {
    this.isMoving = !1, this.interval && (clearInterval(this.interval), this.interval = null);
  }
}
function wt(e) {
  return {
    isDragging: !1,
    insertType: null,
    meet: null,
    ghost: vt(e),
    edgeMoveController: new xt(e),
    startX: 0,
    startY: 0,
    pointerId: null
  };
}
const Et = 5;
function Me(e, t, n, o = !1) {
  if (e.spacePressed) return !1;
  const s = n.target;
  if (s?.tagName !== "ME-TPC" || !s.nodeObj.parent) return !1;
  if (t.startX = n.clientX, t.startY = n.clientY, t.pointerId = n.pointerId, e.dragged = e.currentNodes, o) {
    Je(e, t);
    const i = e.container.getBoundingClientRect();
    Ue(t.ghost, n.clientX - i.x, n.clientY - i.y);
  }
  return !0;
}
function Ue(e, t, n) {
  e.style.transform = `translate(${t - 10}px, ${n - 10}px)`, e.style.display = "block";
}
function Je(e, t) {
  const { dragged: n } = e;
  if (!n) return;
  const o = document.activeElement;
  o && o.isContentEditable && o.blur(), t.isDragging = !0, n.length > 1 ? t.ghost.innerHTML = n.length + "" : t.ghost.innerHTML = n[0].innerHTML;
  for (const s of n)
    s.parentElement.parentElement.style.opacity = "0.5";
  e.panHelper.clear();
}
function Ct(e, t, n) {
  const { dragged: o } = e;
  if (!o || t.pointerId !== n.pointerId) return;
  const s = n.clientX - t.startX, i = n.clientY - t.startY, l = Math.sqrt(s * s + i * i);
  if (!t.isDragging && l > Et && Je(e, t), !t.isDragging) return;
  const c = e.container.getBoundingClientRect();
  Ue(t.ghost, n.clientX - c.x, n.clientY - c.y), n.clientX < c.x + 50 ? t.edgeMoveController.move(1, 0) : n.clientX > c.x + c.width - 50 ? t.edgeMoveController.move(-1, 0) : n.clientY < c.y + 50 ? t.edgeMoveController.move(0, 1) : n.clientY > c.y + c.height - 50 ? t.edgeMoveController.move(0, -1) : t.edgeMoveController.stop(), re(t.meet);
  const r = 12 * e.scaleVal, a = document.elementFromPoint(n.clientX, n.clientY - r);
  if (Ae(a, o)) {
    t.meet = a;
    const d = a.getBoundingClientRect(), h = d.y;
    n.clientY > h + d.height ? t.insertType = "after" : t.insertType = "in";
  } else {
    const d = document.elementFromPoint(n.clientX, n.clientY + r);
    if (Ae(d, o)) {
      t.meet = d;
      const u = d.getBoundingClientRect().y;
      n.clientY < u ? t.insertType = "before" : t.insertType = "in";
    } else
      t.insertType = null, t.meet = null;
  }
  t.meet && bt(t.meet, t.insertType);
}
function St(e, t, n) {
  const { dragged: o } = e;
  if (!(!o || t.pointerId !== n.pointerId)) {
    t.edgeMoveController.stop();
    for (const s of o)
      s.parentElement.parentElement.style.opacity = "1";
    t.ghost.style.display = "none", t.ghost.innerHTML = "", t.isDragging && t.meet && (re(t.meet), t.insertType === "before" ? e.moveNodeBefore(o, t.meet) : t.insertType === "after" ? e.moveNodeAfter(o, t.meet) : t.insertType === "in" && e.moveNodeIn(o, t.meet)), e.dragged = null, t.isDragging = !1, t.insertType = null, t.meet = null, t.pointerId = null;
  }
}
function Pe(e, t) {
  const { dragged: n } = e;
  if (n) {
    t.edgeMoveController.stop();
    for (const o of n)
      o.parentElement.parentElement.style.opacity = "1";
    t.meet && re(t.meet), t.ghost.style.display = "none", t.ghost.innerHTML = "", e.dragged = null, t.isDragging = !1, t.insertType = null, t.meet = null, t.pointerId = null;
  }
}
function Nt(e) {
  return () => {
  };
}
const $ = {
  LHS: "lhs",
  RHS: "rhs"
}, Tt = function() {
  this.nodes.innerHTML = "";
  const e = this.createTopic(this.nodeData);
  ve.call(this, e, this.nodeData), e.draggable = !1;
  const t = document.createElement("me-root");
  t.appendChild(e);
  const n = this.nodeData.children || [];
  if (this.direction === 2) {
    let o = 0, s = 0;
    n.map((i) => {
      i.direction === 0 ? o += 1 : i.direction === 1 ? s += 1 : o <= s ? (i.direction = 0, o += 1) : (i.direction = 1, s += 1);
    });
  }
  kt(this, n, t);
}, kt = function(e, t, n) {
  const o = document.createElement("me-main");
  o.className = $.LHS;
  const s = document.createElement("me-main");
  s.className = $.RHS;
  for (let i = 0; i < t.length; i++) {
    const l = t[i], { grp: c } = e.createWrapper(l);
    e.direction === 2 ? l.direction === 0 ? o.appendChild(c) : s.appendChild(c) : e.direction === 0 ? o.appendChild(c) : s.appendChild(c);
  }
  e.nodes.appendChild(o), e.nodes.appendChild(n), e.nodes.appendChild(s), e.nodes.appendChild(e.lines), e.nodes.appendChild(e.labelContainer);
}, _t = function(e, t) {
  const n = document.createElement("me-children");
  for (let o = 0; o < t.length; o++) {
    const s = t[o], { grp: i } = e.createWrapper(s);
    n.appendChild(i);
  }
  return n;
}, Ze = function(e, t) {
  const o = (this?.el ? this.el : t || document).querySelector(`[data-nodeid="me${e}"]`);
  if (!o) throw new Error(`FindEle: Node ${e} not found, maybe it's collapsed.`);
  return o;
}, ve = function(e, t) {
  if (e.innerHTML = "", t.style) {
    const n = t.style;
    for (const o in n)
      e.style[o] = n[o];
  }
  if (t.dangerouslySetInnerHTML) {
    e.innerHTML = t.dangerouslySetInnerHTML;
    return;
  }
  if (t.image) {
    const n = t.image;
    if (n.url && n.width && n.height) {
      const o = document.createElement("img");
      o.src = this.imageProxy ? this.imageProxy(n.url) : n.url, o.style.width = n.width + "px", o.style.height = n.height + "px", n.fit && (o.style.objectFit = n.fit), e.appendChild(o), e.image = o;
    }
  } else e.image && (e.image = void 0);
  {
    const n = document.createElement("span");
    n.className = "text", this.markdown ? n.innerHTML = this.markdown(t.topic, t) : n.textContent = t.topic, e.appendChild(n), e.text = n;
  }
  if (t.hyperLink) {
    const n = document.createElement("a");
    n.className = "hyper-link", n.target = "_blank", n.innerText = "🔗", n.href = t.hyperLink, e.appendChild(n), e.link = n;
  } else e.link && (e.link = void 0);
  if (t.icons && t.icons.length) {
    const n = document.createElement("span");
    n.className = "icons", n.innerHTML = t.icons.map((o) => `<span>${de(o)}</span>`).join(""), e.appendChild(n), e.icons = n;
  } else e.icons && (e.icons = void 0);
  if (t.tags && t.tags.length) {
    const n = document.createElement("div");
    n.className = "tags", t.tags.forEach((o) => {
      const s = document.createElement("span");
      typeof o == "string" ? s.textContent = o : (s.textContent = o.text, o.className && (s.className = o.className), o.style && Object.assign(s.style, o.style)), n.appendChild(s);
    }), e.appendChild(n), e.tags = n;
  } else e.tags && (e.tags = void 0);
}, Dt = function(e, t) {
  const n = document.createElement("me-wrapper"), { p: o, tpc: s } = this.createParent(e);
  if (n.appendChild(o), !t && e.children && e.children.length > 0) {
    const i = xe(e.expanded);
    if (o.appendChild(i), e.expanded !== !1) {
      const l = _t(this, e.children);
      n.appendChild(l);
    }
  }
  return { grp: n, top: o, tpc: s };
}, Lt = function(e) {
  const t = document.createElement("me-parent"), n = this.createTopic(e);
  return ve.call(this, n, e), t.appendChild(n), { p: t, tpc: n };
}, At = function(e) {
  const t = document.createElement("me-children");
  return t.append(...e), t;
}, Mt = function(e) {
  const t = document.createElement("me-tpc");
  return t.nodeObj = e, t.dataset.nodeid = "me" + e.id, t;
};
function Qe(e) {
  const t = document.createRange();
  t.selectNodeContents(e);
  const n = window.getSelection();
  n && (n.removeAllRanges(), n.addRange(t));
}
const Pt = function(e) {
  if (!e) return;
  const t = document.createElement("div"), n = e.nodeObj, o = n.topic, { offsetLeft: s, offsetTop: i } = A(this.nodes, e);
  this.nodes.appendChild(t), t.id = "input-box", t.textContent = o, t.contentEditable = "plaintext-only", t.spellcheck = !1;
  const l = getComputedStyle(e);
  t.style.cssText = `
  left: ${s}px;
  top: ${i}px;
  min-width:${e.offsetWidth - 8}px;
  color:${l.color};
  font-size:${l.fontSize};
  padding:${l.padding};
  margin:${l.margin}; 
  background-color:${l.backgroundColor !== "rgba(0, 0, 0, 0)" && l.backgroundColor};
  border: ${l.border};
  border-radius:${l.borderRadius}; `, this.direction === 0 && (t.style.right = "0"), e.style.opacity = "0", Qe(t), this.bus.fire("operation", {
    name: "beginEdit",
    obj: e.nodeObj
  }), t.addEventListener("keydown", (c) => {
    if (c.stopPropagation(), c.isComposing) return;
    const r = c.key;
    if (r === "Enter" || r === "Tab") {
      if (c.shiftKey) return;
      c.preventDefault(), t.blur(), this.container.focus();
    } else r === "Escape" && (c.preventDefault(), t.textContent = o, t.blur(), this.container.focus());
  }), t.addEventListener("blur", () => {
    if (!t) return;
    e.style.opacity = "1", t.remove();
    const c = t.innerText?.trim() || "";
    c === o || c === "" || (n.topic = c, this.markdown ? e.text.innerHTML = this.markdown(n.topic, n) : e.text.textContent = c, this.linkDiv(), this.bus.fire("operation", {
      name: "finishEdit",
      obj: n,
      origin: o
    }));
  });
}, xe = function(e) {
  const t = document.createElement("me-epd");
  return t.expanded = e !== !1, t.className = e !== !1 ? "minus" : "", t;
}, z = (e) => {
  const t = e.parent?.children, n = t?.indexOf(e) ?? 0;
  return { siblings: t, index: n };
};
function Ot(e) {
  const { siblings: t, index: n } = z(e);
  if (t === void 0) return;
  const o = t[n];
  n === 0 ? (t[n] = t[t.length - 1], t[t.length - 1] = o) : (t[n] = t[n - 1], t[n - 1] = o);
}
function $t(e) {
  const { siblings: t, index: n } = z(e);
  if (t === void 0) return;
  const o = t[n];
  n === t.length - 1 ? (t[n] = t[0], t[0] = o) : (t[n] = t[n + 1], t[n + 1] = o);
}
function et(e) {
  const { siblings: t, index: n } = z(e);
  return t === void 0 ? 0 : (t.splice(n, 1), t.length);
}
function Ht(e, t, n) {
  const { siblings: o, index: s } = z(n);
  o !== void 0 && (t === "before" ? o.splice(s, 0, e) : o.splice(s + 1, 0, e));
}
function jt(e, t) {
  const { siblings: n, index: o } = z(e);
  n !== void 0 && (n[o] = t, t.children = [e]);
}
function It(e, t, n) {
  if (et(t), n.parent?.parent || (t.direction = n.direction), e === "in")
    n.children ? n.children.push(t) : n.children = [t];
  else {
    t.direction !== void 0 && (t.direction = n.direction);
    const { siblings: o, index: s } = z(n);
    if (o === void 0) return;
    e === "before" ? o.splice(s, 0, t) : o.splice(s + 1, 0, t);
  }
}
const Rt = function({ map: e, direction: t }, n) {
  if (t === 0)
    return 0;
  if (t === 1)
    return 1;
  if (t === 2) {
    const o = e.querySelector(".lhs")?.childElementCount || 0, s = e.querySelector(".rhs")?.childElementCount || 0;
    return o <= s ? (n.direction = 0, 0) : (n.direction = 1, 1);
  }
}, tt = function(e, t, n) {
  const o = n.children[0].children[0], s = t.parentElement;
  if (s.tagName === "ME-PARENT") {
    if (U(o), s.children[1])
      s.nextSibling.appendChild(n);
    else {
      const i = e.createChildren([n]);
      s.appendChild(xe(!0)), s.insertAdjacentElement("afterend", i);
    }
    e.linkDiv(n.offsetParent);
  } else s.tagName === "ME-ROOT" && (Rt(e, o.nodeObj) === 0 ? e.container.querySelector(".lhs")?.appendChild(n) : e.container.querySelector(".rhs")?.appendChild(n), e.linkDiv());
}, Bt = function(e, t) {
  const n = e.parentNode;
  if (t === 0) {
    const o = n.parentNode.parentNode;
    o.tagName !== "ME-MAIN" && (o.previousSibling.children[1].remove(), o.remove());
  }
  n.parentNode.remove();
}, nt = {
  before: "beforebegin",
  after: "afterend"
}, U = function(e) {
  const n = e.parentElement.parentElement.lastElementChild;
  n?.tagName === "svg" && n?.remove();
}, Wt = function(e, t) {
  const n = e.nodeObj, o = ie(n);
  o.style && t.style && (t.style = Object.assign(o.style, t.style));
  const s = Object.assign(n, t);
  ve.call(this, e, s), this.linkDiv(), this.bus.fire("operation", {
    name: "reshapeNode",
    obj: s,
    origin: o
  });
}, we = function(e, t, n) {
  if (!t) return null;
  const o = t.nodeObj;
  o.expanded === !1 && (e.expandNode(t, !0), t = e.findEle(o.id));
  const s = n || e.generateNewObj();
  o.children ? o.children.push(s) : o.children = [s], B(e.nodeData);
  const { grp: i, top: l } = e.createWrapper(s);
  return tt(e, t, i), { newTop: l, newNodeObj: s };
}, Yt = function(e, t, n) {
  const o = t || this.currentNode;
  if (!o) return;
  const s = o.nodeObj;
  if (s.parent) {
    if (!s.parent?.parent && this.direction === 2) {
      const a = this.map.querySelector(".lhs")?.childElementCount || 0, d = this.map.querySelector(".rhs")?.childElementCount || 0;
      if (!a || !d) {
        this.addChild(this.findEle(s.parent.id), n);
        return;
      }
    }
  } else {
    this.addChild();
    return;
  }
  const i = n || this.generateNewObj();
  if (!s.parent?.parent) {
    const a = o.closest("me-main").className === $.LHS ? 0 : 1;
    i.direction = a;
  }
  Ht(i, e, s), B(this.nodeData);
  const l = o.parentElement, { grp: c, top: r } = this.createWrapper(i);
  l.parentElement.insertAdjacentElement(nt[e], c), this.linkDiv(c.offsetParent), n || this.editTopic(r.firstChild), this.bus.fire("operation", {
    name: "insertSibling",
    type: e,
    obj: i
  }), this.selectNode(r.firstChild, !0);
}, Xt = function(e, t) {
  const n = e || this.currentNode;
  if (!n) return;
  U(n);
  const o = n.nodeObj;
  if (!o.parent)
    return;
  const s = t || this.generateNewObj();
  jt(o, s), B(this.nodeData);
  const i = n.parentElement.parentElement, { grp: l, top: c } = this.createWrapper(s, !0);
  c.appendChild(xe(!0)), i.insertAdjacentElement("afterend", l);
  const r = this.createChildren([i]);
  c.insertAdjacentElement("afterend", r), this.linkDiv(), t || this.editTopic(c.firstChild), this.selectNode(c.firstChild, !0), this.bus.fire("operation", {
    name: "insertParent",
    obj: s
  });
}, Ft = function(e, t) {
  const n = e || this.currentNode;
  if (!n) return;
  const o = we(this, n, t);
  if (!o) return;
  const { newTop: s, newNodeObj: i } = o;
  this.bus.fire("operation", {
    name: "addChild",
    obj: i
  }), t || this.editTopic(s.firstChild), this.selectNode(s.firstChild, !0);
}, Kt = function(e, t) {
  const n = ie(e.nodeObj);
  me(n);
  const o = we(this, t, n);
  if (!o) return;
  const { newNodeObj: s } = o;
  this.selectNode(this.findEle(s.id)), this.bus.fire("operation", {
    name: "copyNode",
    obj: s
  });
}, Vt = function(e, t) {
  const n = [];
  for (let o = 0; o < e.length; o++) {
    const s = e[o], i = ie(s.nodeObj);
    me(i);
    const l = we(this, t, i);
    if (!l) return;
    const { newNodeObj: c } = l;
    n.push(c);
  }
  this.unselectNodes(this.currentNodes), this.selectNodes(n.map((o) => this.findEle(o.id))), this.bus.fire("operation", {
    name: "copyNodes",
    objs: n
  });
}, zt = function(e) {
  const t = e || this.currentNode;
  if (!t) return;
  const n = t.nodeObj;
  Ot(n);
  const o = t.parentNode.parentNode;
  o.parentNode.insertBefore(o, o.previousSibling), this.linkDiv(), this.bus.fire("operation", {
    name: "moveUpNode",
    obj: n
  });
}, Gt = function(e) {
  const t = e || this.currentNode;
  if (!t) return;
  const n = t.nodeObj;
  $t(n);
  const o = t.parentNode.parentNode;
  o.nextSibling ? o.nextSibling.insertAdjacentElement("afterend", o) : o.parentNode.prepend(o), this.linkDiv(), this.bus.fire("operation", {
    name: "moveDownNode",
    obj: n
  });
}, qt = function(e) {
  if (e = ye(e), e.length === 0) return;
  for (const n of e) {
    const o = n.nodeObj, s = et(o);
    Bt(n, s);
  }
  const t = e[e.length - 1];
  this.selectNode(this.findEle(t.nodeObj.parent.id)), this.linkDiv(), this.bus.fire("operation", {
    name: "removeNodes",
    objs: e.map((n) => n.nodeObj)
  });
}, Ee = (e, t, n, o) => {
  e = ye(e);
  let s = n.nodeObj;
  t === "in" && s.expanded === !1 && (o.expandNode(n, !0), n = o.findEle(s.id), s = n.nodeObj), t === "after" && (e = e.reverse());
  const i = [];
  for (const c of e) {
    const r = c.nodeObj;
    if (It(t, r, s), B(o.nodeData), t === "in") {
      const a = c.parentElement;
      tt(o, n, a.parentElement);
    } else {
      U(c);
      const a = c.parentElement.parentNode;
      i.includes(a.parentElement) || i.push(a.parentElement), n.parentElement.parentNode.insertAdjacentElement(nt[t], a);
    }
  }
  for (const c of i)
    c.childElementCount === 0 && c.tagName !== "ME-MAIN" && (c.previousSibling.children[1].remove(), c.remove());
  o.linkDiv(), o.scrollIntoView(e[e.length - 1]);
  const l = t === "before" ? "moveNodeBefore" : t === "after" ? "moveNodeAfter" : "moveNodeIn";
  o.bus.fire("operation", {
    name: l,
    objs: e.map((c) => c.nodeObj),
    toObj: s
  });
}, Ut = function(e, t) {
  Ee(e, "in", t, this);
}, Jt = function(e, t) {
  Ee(e, "before", t, this);
}, Zt = function(e, t) {
  Ee(e, "after", t, this);
}, Qt = function(e) {
  const t = e || this.currentNode;
  t && (t.nodeObj.dangerouslySetInnerHTML || this.editTopic(t));
}, en = function(e, t) {
  e.text.textContent = t, e.nodeObj.topic = t, this.linkDiv();
}, ot = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  addChild: Ft,
  beginEdit: Qt,
  copyNode: Kt,
  copyNodes: Vt,
  insertParent: Xt,
  insertSibling: Yt,
  moveDownNode: Gt,
  moveNodeAfter: Zt,
  moveNodeBefore: Jt,
  moveNodeIn: Ut,
  moveUpNode: zt,
  removeNodes: qt,
  reshapeNode: Wt,
  rmSubline: U,
  setNodeTopic: en
}, Symbol.toStringTag, { value: "Module" }));
function tn(e) {
  return {
    nodeData: e.isFocusMode ? e.nodeDataBackup : e.nodeData,
    arrows: e.arrows,
    summaries: e.summaries,
    direction: e.direction,
    theme: e.theme,
    compact: e.compact,
    meta: e.meta
  };
}
const nn = function(e, t = !1) {
  const n = this.container, o = e.getBoundingClientRect(), s = n.getBoundingClientRect();
  if (t || o.top > s.bottom - 50 || o.bottom < s.top + 50 || o.left > s.right - 50 || o.right < s.left + 50) {
    const l = o.left + o.width / 2, c = o.top + o.height / 2, r = s.left + s.width / 2, a = s.top + s.height / 2, d = l - r, h = c - a;
    this.move(-d, -h, !0);
  }
}, on = function(e, t, n) {
  this.clearSelection(), this.scrollIntoView(e), this.selection?.select(e), t && this.bus.fire("selectNewNode", e.nodeObj);
}, sn = function(e) {
  this.selection?.select(e);
}, rn = function(e) {
  this.selection?.deselect(e);
}, ln = function() {
  this.unselectNodes(this.currentNodes), this.unselectSummary(), this.unselectArrow();
}, Ce = function(e) {
  return JSON.stringify(e, (t, n) => {
    if (!(t === "parent" && typeof n != "string"))
      return n;
  });
}, cn = function() {
  const e = tn(this);
  return Ce(e);
}, an = function() {
  return JSON.parse(this.getDataString());
}, dn = function() {
  this.editable = !0;
}, hn = function() {
  this.editable = !1;
}, fn = function(e, t = { x: 0, y: 0 }) {
  if (e < this.scaleMin && e < this.scaleVal || e > this.scaleMax && e > this.scaleVal) return;
  const n = this.container.getBoundingClientRect(), o = t.x ? t.x - n.left - n.width / 2 : 0, s = t.y ? t.y - n.top - n.height / 2 : 0, { dx: i, dy: l } = Se(this), c = this.map.style.transform, { x: r, y: a } = be(c), d = r - i, h = a - l, u = this.scaleVal, p = (-o + d) * (1 - e / u), v = (-s + h) * (1 - e / u);
  this.map.style.transform = `translate3d(${r - p}px, ${a - v}px, 0) scale(${e})`, this.scaleVal = e, this.bus.fire("scale", e);
}, un = function() {
  const e = this.nodes.offsetHeight / this.container.offsetHeight, t = this.nodes.offsetWidth / this.container.offsetWidth, n = 1 / Math.max(1, Math.max(e, t));
  this.scaleVal = n;
  const { dx: o, dy: s } = Se(this, !0);
  this.map.style.transform = `translate3d(${o}px, ${s}px, 0) scale(${n})`, this.bus.fire("scale", n);
}, pn = function(e, t, n = !1) {
  const { map: o, scaleVal: s, bus: i, container: l, nodes: c } = this;
  if (n && o.style.transition === "transform 0.3s")
    return;
  const r = o.style.transform;
  let { x: a, y: d } = be(r);
  const h = l.getBoundingClientRect(), u = c.getBoundingClientRect(), p = u.left < h.right && u.right > h.left, v = u.top < h.bottom && u.bottom > h.top;
  if (p) {
    const m = u.left + e, y = u.right + e;
    (m >= h.right || y <= h.left) && (e = 0);
  }
  if (v) {
    const m = u.top + t, y = u.bottom + t;
    (m >= h.bottom || y <= h.top) && (t = 0);
  }
  a += e, d += t, n && (o.style.transition = "transform 0.3s", setTimeout(() => {
    o.style.transition = "none";
  }, 300)), o.style.transform = `translate3d(${a}px, ${d}px, 0) scale(${s})`, i.fire("move", { dx: e, dy: t });
}, Se = (e, t = !1) => {
  const { container: n, map: o, nodes: s } = e;
  let i, l;
  if (e.alignment === "nodes" || t)
    i = (n.offsetWidth - s.offsetWidth) / 2, l = (n.offsetHeight - s.offsetHeight) / 2, o.style.transformOrigin = "50% 50%";
  else {
    const c = o.querySelector("me-root"), r = c.offsetTop, a = c.offsetLeft, d = c.offsetWidth, h = c.offsetHeight;
    i = n.offsetWidth / 2 - a - d / 2, l = n.offsetHeight / 2 - r - h / 2, o.style.transformOrigin = `${a + d / 2}px 50%`;
  }
  return { dx: i, dy: l };
}, gn = function() {
  const { map: e, container: t } = this, { dx: n, dy: o } = Se(this);
  t.scrollTop = 0, t.scrollLeft = 0, e.style.transform = `translate3d(${n}px, ${o}px, 0) scale(${this.scaleVal})`;
}, mn = function(e) {
  e(this);
}, yn = function(e) {
  e.nodeObj.parent && (this.clearSelection(), this.tempDirection === null && (this.tempDirection = this.direction), this.isFocusMode || (this.nodeDataBackup = this.nodeData, this.isFocusMode = !0), this.nodeData = e.nodeObj, this.initRight(), this.toCenter());
}, bn = function() {
  this.isFocusMode = !1, this.tempDirection !== null && (this.nodeData = this.nodeDataBackup, this.direction = this.tempDirection, this.tempDirection = null, this.refresh(), this.toCenter());
}, vn = function() {
  this.direction = 0, this.refresh(), this.toCenter(), this.bus.fire("changeDirection", this.direction);
}, xn = function() {
  this.direction = 1, this.refresh(), this.toCenter(), this.bus.fire("changeDirection", this.direction);
}, wn = function() {
  this.direction = 2, this.refresh(), this.toCenter(), this.bus.fire("changeDirection", this.direction);
}, En = function(e, t) {
  const n = e.nodeObj;
  typeof t == "boolean" ? n.expanded = t : n.expanded !== !1 ? n.expanded = !1 : n.expanded = !0;
  const o = e.getBoundingClientRect(), s = {
    x: o.left,
    y: o.top
  }, i = e.parentNode, l = i.children[1];
  if (l.expanded = n.expanded, l.className = n.expanded ? "minus" : "", U(e), n.expanded) {
    const h = this.createChildren(
      n.children.map((u) => this.createWrapper(u).grp)
    );
    i.parentNode.appendChild(h);
  } else
    i.parentNode.children[1].remove();
  this.linkDiv(e.closest("me-main > me-wrapper"));
  const c = e.getBoundingClientRect(), r = {
    x: c.left,
    y: c.top
  }, a = s.x - r.x, d = s.y - r.y;
  this.move(a, d), this.bus.fire("expandNode", n);
}, Cn = function(e, t) {
  const n = e.nodeObj, o = e.getBoundingClientRect(), s = {
    x: o.left,
    y: o.top
  };
  K(n, t ?? !n.expanded), this.refresh();
  const i = this.findEle(n.id).getBoundingClientRect(), l = {
    x: i.left,
    y: i.top
  }, c = s.x - l.x, r = s.y - l.y;
  this.move(c, r);
}, Sn = function(e) {
  this.clearSelection(), e && (e = JSON.parse(JSON.stringify(e)), this.nodeData = e.nodeData, this.arrows = e.arrows || [], this.summaries = e.summaries || [], e.meta && (this.meta = e.meta), e.theme && this.changeTheme(e.theme)), B(this.nodeData), this.layout(), this.linkDiv();
}, Nn = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  cancelFocus: bn,
  clearSelection: ln,
  disableEdit: hn,
  enableEdit: dn,
  expandNode: En,
  expandNodeAll: Cn,
  focusNode: yn,
  getData: an,
  getDataString: cn,
  initLeft: vn,
  initRight: xn,
  initSide: wn,
  install: mn,
  move: pn,
  refresh: Sn,
  scale: fn,
  scaleFit: un,
  scrollIntoView: nn,
  selectNode: on,
  selectNodes: sn,
  stringifyData: Ce,
  toCenter: gn,
  unselectNodes: rn
}, Symbol.toStringTag, { value: "Module" })), Oe = "MIND-ELIXIR-WAIT-COPY", Tn = 40, kn = 10, _n = ({ deltaMode: e, deltaY: t, viewportHeight: n }) => e === WheelEvent.DOM_DELTA_LINE ? t * Tn : e === WheelEvent.DOM_DELTA_PAGE ? t * n : t, Dn = ({ deltaMode: e, deltaY: t, scaleSensitivity: n, viewportHeight: o }) => {
  const i = -_n({ deltaMode: e, deltaY: t, viewportHeight: o }) / kn * n;
  return Math.max(-n, Math.min(n, i));
}, st = (e, t, n) => {
  t !== 0 && e.scale(e.scaleVal + t, n);
}, Ln = (e, t) => {
  const n = e.map.querySelectorAll(`.${t}>me-wrapper>me-parent>me-tpc`);
  n.length !== 0 && e.selectNode(n[Math.ceil(n.length / 2) - 1]);
}, An = (e) => {
  e.selectNode(e.map.querySelector("me-root>me-tpc"));
}, Mn = function(e, t) {
  const n = t.parentElement.parentElement.parentElement.previousSibling;
  if (n) {
    const o = n.firstChild;
    e.selectNode(o);
  }
}, Pn = function(e, t) {
  const n = t.parentElement.nextSibling;
  if (n && n.firstChild) {
    const o = n.firstChild.firstChild.firstChild;
    e.selectNode(o);
  }
}, $e = function(e, t) {
  const n = e.currentNode || e.currentNodes?.[0];
  if (!n) return;
  const o = n.nodeObj, s = n.offsetParent.offsetParent.parentElement;
  o.parent ? s.className === t ? Pn(e, n) : o.parent?.parent ? Mn(e, n) : An(e) : Ln(e, t);
}, He = function(e, t) {
  const n = e.currentNode;
  if (!n || !n.nodeObj.parent) return;
  const s = t + "Sibling", i = n.parentElement.parentElement[s];
  i ? e.selectNode(i.firstChild.firstChild) : e.selectNode(n);
}, je = function(e, t, n) {
  const o = t === "in" ? e.scaleSensitivity : -e.scaleSensitivity;
  st(e, o, n);
}, On = (e, t) => {
  const n = Dn({
    deltaMode: t.deltaMode,
    deltaY: t.deltaY,
    scaleSensitivity: e.scaleSensitivity,
    viewportHeight: e.container.clientHeight || window.innerHeight
  });
  st(e, n, { x: t.clientX, y: t.clientY });
};
function $n(e, t) {
  t = t === !0 ? {} : t;
  const n = () => {
    e.currentArrow ? e.removeArrow() : e.currentSummary ? e.removeSummary(e.currentSummary.summaryObj.id) : e.currentNodes && e.removeNodes(e.currentNodes);
  };
  let o = !1, s = null;
  const i = (r) => {
    const a = e.nodeData;
    if (r.key === "0")
      for (const d of a.children)
        K(d, !1);
    if (r.key === "=")
      for (const d of a.children)
        K(d, !0);
    if (["1", "2", "3", "4", "5", "6", "7", "8", "9"].includes(r.key))
      for (const d of a.children)
        K(d, !0, Number(r.key) - 1);
    e.refresh(), e.toCenter(), o = !1, s && (clearTimeout(s), s = null, e.container.removeEventListener("keydown", i));
  }, l = {
    Enter: (r) => {
      r.shiftKey ? e.insertSibling("before") : r.ctrlKey || r.metaKey ? e.insertParent() : e.insertSibling("after");
    },
    Tab: () => {
      e.addChild();
    },
    F1: () => {
      e.toCenter();
    },
    F2: () => {
      e.currentSummary ? e.editSummary(e.currentSummary) : e.currentArrow ? e.editArrowLabel(e.currentArrow) : e.beginEdit();
    },
    ArrowUp: (r) => {
      if (r.altKey)
        e.moveUpNode();
      else {
        if (r.metaKey || r.ctrlKey)
          return e.initSide();
        He(e, "previous");
      }
    },
    ArrowDown: (r) => {
      r.altKey ? e.moveDownNode() : He(e, "next");
    },
    ArrowLeft: (r) => {
      if (r.metaKey || r.ctrlKey)
        return e.initLeft();
      $e(e, $.LHS);
    },
    ArrowRight: (r) => {
      if (r.metaKey || r.ctrlKey)
        return e.initRight();
      $e(e, $.RHS);
    },
    PageUp: () => e.moveUpNode(),
    PageDown: () => {
      e.moveDownNode();
    },
    "=": (r) => {
      (r.metaKey || r.ctrlKey) && je(e, "in");
    },
    "-": (r) => {
      (r.metaKey || r.ctrlKey) && je(e, "out");
    },
    0: (r) => {
      if (r.metaKey || r.ctrlKey) {
        if (o)
          return;
        e.scale(1);
      }
    },
    k: (r) => {
      (r.metaKey || r.ctrlKey) && (o = !0, s && (clearTimeout(s), e.container.removeEventListener("keydown", i)), s = window.setTimeout(() => {
        o = !1, s = null;
      }, 2e3), e.container.addEventListener("keydown", i));
    },
    Delete: n,
    Backspace: n,
    ...t
  };
  e.container.onkeydown = (r) => {
    if ((r.ctrlKey || r.metaKey) && ["c", "v", "x"].includes(r.key) || r.preventDefault(), !e.editable) return;
    const d = l[r.key];
    d && d(r);
  };
  const c = (r) => {
    if (r.target instanceof HTMLElement && r.target.id === "input-box" || e.currentNodes.length === 0) return !1;
    if (r.clipboardData) {
      const a = ye(e.currentNodes).map((h) => h.nodeObj), d = Ce({
        magic: Oe,
        data: a
      });
      return r.clipboardData.setData("text/plain", d), r.preventDefault(), !0;
    }
    return !1;
  };
  e.container.addEventListener("copy", c), e.container.addEventListener("cut", (r) => {
    c(r) && n();
  }), e.container.addEventListener("paste", (r) => {
    const a = r.clipboardData?.getData("text/plain");
    if (a)
      try {
        const d = JSON.parse(a);
        if (d && d.magic === Oe && Array.isArray(d.data)) {
          const h = d.data, u = h.map((p) => ({ nodeObj: p }));
          h.length > 0 && e.currentNode && (e.copyNodes(u, e.currentNode), r.preventDefault());
          return;
        }
      } catch {
      }
    e.pasteHandler && e.pasteHandler(r);
  });
}
function Hn(e) {
  const { panHelper: t, container: n } = e;
  let o = null;
  e.spacePressed = !1;
  const s = {
    lastTap: 0,
    lastTapTarget: null,
    DOUBLE_CLICK_THRESHOLD: 300,
    detect(f, b) {
      if (f.button !== 0) {
        this.clear();
        return;
      }
      const w = (/* @__PURE__ */ new Date()).getTime(), S = w - this.lastTap, C = S < this.DOUBLE_CLICK_THRESHOLD && S > 0 && this.lastTapTarget === f.target;
      this.lastTap = w, this.lastTapTarget = f.target, C && b(f);
    },
    clear() {
      this.lastTap = 0, this.lastTapTarget = null;
    }
  }, i = {
    Idle: 0,
    Pinch: 1,
    DragWait: 2,
    Drag: 3,
    Pan: 4,
    BoxSelect: 5
  };
  e.ptState = i.Idle;
  const l = {
    lastDistance: null,
    activePointers: /* @__PURE__ */ new Map(),
    handlePointerDown(f) {
      if (f.pointerType !== "touch") return !1;
      if (this.activePointers.set(f.pointerId, { x: f.clientX, y: f.clientY }), this.activePointers.size >= 2) {
        const [b, w] = Array.from(this.activePointers.values());
        return this.lastDistance = Le(b, w), !0;
      }
      return !1;
    },
    handlePointerMove(f) {
      if (f.pointerType !== "touch" || !this.activePointers.has(f.pointerId)) return !1;
      if (this.activePointers.set(f.pointerId, { x: f.clientX, y: f.clientY }), this.activePointers.size >= 2) {
        const [b, w] = Array.from(this.activePointers.values()), S = Le(b, w);
        if (this.lastDistance !== null && this.lastDistance > 0) {
          const C = S / this.lastDistance;
          e.scale(e.scaleVal * C, {
            x: (b.x + w.x) / 2,
            y: (b.y + w.y) / 2
          });
        }
        return this.lastDistance = S, !0;
      }
      return !1;
    },
    handlePointerUp(f) {
      f.pointerType === "touch" && (this.activePointers.delete(f.pointerId), this.activePointers.size < 2 && (this.lastDistance = null));
    },
    clear() {
      this.activePointers.clear(), this.lastDistance = null;
    }
  }, c = wt(e), r = {
    timer: null,
    startPos: null,
    pointerId: null,
    DURATION: 500,
    MOVE_THRESHOLD: 10,
    clear() {
      this.timer !== null && (clearTimeout(this.timer), this.timer = null, this.startPos = null, this.pointerId = null);
    },
    start(f, b) {
      this.timer = window.setTimeout(() => {
        b(f), this.timer = null, this.startPos = null, this.pointerId = null;
      }, this.DURATION), this.startPos = { x: f.clientX, y: f.clientY }, this.pointerId = f.pointerId;
    },
    handleMove(f) {
      if (this.timer !== null && this.startPos !== null && f.pointerId === this.pointerId) {
        const b = f.clientX - this.startPos.x, w = f.clientY - this.startPos.y;
        Math.sqrt(b * b + w * w) > this.MOVE_THRESHOLD && this.clear();
      }
    }
  }, a = (f, b) => {
    if (f.closest("#input-box")) return !1;
    const w = f.closest(".svg-label"), S = f.closest(".topiclinks, .summary"), C = w ? { type: w.dataset.type, element: document.getElementById(w.dataset.svgId) } : S ? { type: S.classList.contains("topiclinks") ? "arrow" : "summary", element: f.closest("g") } : null;
    if (!C?.type || !C?.element) return !1;
    const { type: T, element: D } = C;
    return e.clearSelection(), T === "arrow" ? b ? e.editArrowLabel(D) : e.selectArrow(D) : b ? e.editSummary(D) : e.selectSummary(D), !0;
  }, d = (f) => {
    if (f.pointerType === "mouse" && f.button !== 0) return;
    if (e.helper1?.moved) {
      e.helper1.clear();
      return;
    }
    if (e.helper2?.moved) {
      e.helper2.clear();
      return;
    }
    if (t.moved) {
      t.clear();
      return;
    }
    if (c?.isDragging)
      return;
    const b = f.target;
    b.tagName === "ME-EPD" && (f.ctrlKey || f.metaKey ? e.expandNodeAll(b.previousSibling) : e.expandNode(b.previousSibling));
  }, h = (f) => {
    if (!e.editable) return;
    const b = f.target;
    if (ne(b)) {
      e.selectNode(b), e.beginEdit(b);
      return;
    }
    a(b, !0);
  }, u = (f) => {
    if (f.pointerType === "touch" && l.handlePointerDown(f)) {
      e.ptState = i.Pinch, r.clear(), t.clear(), (c.isDragging || c.pointerId !== null) && Pe(e, c);
      return;
    }
    if (e.ptState === i.Pinch) return;
    const b = f.target;
    if (e.editable && b.className === "map-container" && f.button === 0 && f.pointerType === "mouse") {
      e.ptState = i.BoxSelect;
      return;
    }
    if (t.handlePointerDown(f), t.mousedown && (e.ptState = i.Pan), f.button === 0 || f.pointerType === "touch")
      if (ne(b)) {
        e.selection?.cancel();
        const S = e.currentNodes || [];
        if (f.ctrlKey || f.metaKey || e.mobileMultiSelect ? S.includes(b) ? o = b : ((e.currentArrow || e.currentSummary) && e.clearSelection(), e.selection?.select(b)) : S.includes(b) || e.selectNode(b), !e.editable) return;
        f.pointerType === "touch" ? (e.ptState = i.DragWait, r.start(f, (T) => {
          Me(e, c, T, !0) && (e.ptState = i.Drag, b.setPointerCapture(T.pointerId));
        })) : Me(e, c, f, !1) && (e.ptState = i.Drag, b.setPointerCapture(f.pointerId));
      } else
        a(b, !1);
  }, p = (f) => {
    switch (e.ptState) {
      case i.Pinch:
        l.handlePointerMove(f);
        break;
      case i.DragWait:
        r.handleMove(f), r.timer === null && (e.ptState = i.Pan, t.handlePointerMove(f));
        break;
      case i.Drag:
        Ct(e, c, f);
        break;
      case i.Pan:
        t.handlePointerMove(f);
        break;
    }
  }, v = (f) => {
    f.pointerType === "touch" && l.handlePointerUp(f);
    const b = c.isDragging, w = t.moved;
    switch (e.ptState) {
      case i.DragWait:
        r.clear();
        break;
      case i.Drag:
        St(e, c, f);
        break;
      case i.Pan:
        t.handlePointerUp(f);
        break;
    }
    s.detect(f, h), (e.ptState !== i.Pinch || l.activePointers.size < 2) && (e.ptState = i.Idle), o && (!b && !w && e.selection?.deselect(o), o = null);
  }, m = () => {
    l.clear(), r.clear(), t.clear(), s.clear(), (c.isDragging || c.pointerId !== null) && Pe(e, c), e.ptState = i.Idle, o = null;
  }, y = (f) => {
    f.preventDefault(), f.button === 2 && e.editable && setTimeout(() => {
      if (e.panHelper.moved || e.ptState !== i.Idle && e.ptState !== i.Pan) return;
      const b = f.target;
      ne(b) && !b.classList.contains("selected") && e.selectNode(b), e.bus.fire("showContextMenu", f);
    }, 200);
  }, g = (f) => {
    if (f.stopPropagation(), f.preventDefault(), f.ctrlKey || f.metaKey) return On(e, f);
    if (f.shiftKey) return e.move(-f.deltaY, 0);
    e.move(-f.deltaX, -f.deltaY);
  }, x = (f) => {
    f.code === "Space" && (e.spacePressed = !0, e.container.classList.add("space-pressed"));
  }, E = (f) => {
    f.code === "Space" && (e.spacePressed = !1, e.container.classList.remove("space-pressed"));
  };
  return qe([
    { dom: n, evt: "pointerdown", func: u },
    { dom: n, evt: "pointermove", func: p },
    { dom: n, evt: "pointerup", func: v },
    { dom: n, evt: "pointercancel", func: m },
    { dom: n, evt: "click", func: d },
    { dom: n, evt: "contextmenu", func: y },
    { dom: n, evt: "wheel", func: typeof e.handleWheel == "function" ? e.handleWheel : g },
    { dom: n, evt: "blur", func: m },
    { dom: n, evt: "keydown", func: x },
    { dom: n, evt: "keyup", func: E }
  ]);
}
function jn() {
  return {
    handlers: {},
    addListener: function(e, t) {
      this.handlers[e] === void 0 && (this.handlers[e] = []), this.handlers[e].push(t);
    },
    fire: function(e, ...t) {
      if (this.handlers[e] instanceof Array) {
        const n = this.handlers[e];
        for (let o = 0; o < n.length; o++)
          n[o](...t);
      }
    },
    removeListener: function(e, t) {
      if (!this.handlers[e]) return;
      const n = this.handlers[e];
      if (!t)
        n.length = 0;
      else if (n.length)
        for (let o = 0; o < n.length; o++)
          n[o] === t && this.handlers[e].splice(o, 1);
    }
  };
}
const M = "http://www.w3.org/2000/svg", le = function(e) {
  const t = e.clientWidth, n = e.clientHeight, o = e.dataset, s = Number(o.x), i = Number(o.y), l = o.anchor;
  let c = s;
  l === "middle" ? c = s - t / 2 : l === "end" && (c = s - t), e.style.left = `${c}px`, e.style.top = `${i - n / 2}px`, e.style.visibility = "visible";
}, he = function(e, t, n, o) {
  const { anchor: s = "middle", color: i, dataType: l, svgId: c } = o, r = document.createElement("div");
  r.className = "svg-label", r.style.color = i || "#666";
  const a = "label-" + c;
  return r.id = a, r.innerHTML = e, r.dataset.type = l, r.dataset.svgId = c, r.dataset.x = t.toString(), r.dataset.y = n.toString(), r.dataset.anchor = s, r;
}, it = function(e, t, n) {
  const o = document.createElementNS(M, "path");
  return k(o, {
    d: e,
    stroke: t || "#666",
    fill: "none",
    "stroke-width": n
  }), o;
}, q = function(e) {
  const t = document.createElementNS(M, "svg");
  return t.setAttribute("class", e), t.setAttribute("overflow", "visible"), t;
}, Ie = function() {
  const e = document.createElementNS(M, "line");
  return e.setAttribute("stroke", "#4dc4ff"), e.setAttribute("fill", "none"), e.setAttribute("stroke-width", "2"), e.setAttribute("opacity", "0.45"), e;
}, In = function(e, t, n, o) {
  const s = document.createElementNS(M, "g");
  return [
    {
      name: "line",
      d: e
    },
    {
      name: "arrow1",
      d: t
    },
    {
      name: "arrow2",
      d: n
    }
  ].forEach((l, c) => {
    const r = l.d, a = document.createElementNS(M, "path"), d = {
      d: r,
      stroke: o?.stroke || "rgb(227, 125, 116)",
      fill: "none",
      "stroke-linecap": o?.strokeLinecap || "cap",
      "stroke-width": String(o?.strokeWidth || "2")
    };
    o?.opacity !== void 0 && (d.opacity = String(o.opacity)), k(a, d), c === 0 && a.setAttribute("stroke-dasharray", o?.strokeDasharray || "8,2");
    const h = document.createElementNS(M, "path");
    k(h, {
      d: r,
      stroke: "transparent",
      fill: "none",
      "stroke-width": "15"
    }), s.appendChild(h), s.appendChild(a), s[l.name] = a;
  }), s;
}, rt = function(e, t, n) {
  if (!t) return;
  const o = n.label;
  t.style.opacity = "0";
  const s = t.cloneNode(!0);
  e.nodes.appendChild(s), s.id = "input-box", s.textContent = o, s.contentEditable = "plaintext-only", s.spellcheck = !1, s.style.cssText = `
    left:${t.style.left};
    top:${t.style.top}; 
    max-width: 200px;
  `, Qe(s), e.scrollIntoView(s), s.addEventListener("keydown", (i) => {
    if (i.stopPropagation(), i.isComposing) return;
    const l = i.key;
    if (l === "Enter" || l === "Tab") {
      if (i.shiftKey) return;
      i.preventDefault(), s.blur(), e.container.focus();
    }
  }), s.addEventListener("blur", () => {
    if (!s) return;
    const i = s.innerText?.trim() || "";
    i === "" ? n.label = o : n.label = i, t.style.opacity = "1", s.remove(), i !== o && (e.markdown ? t.innerHTML = e.markdown(n.label, n) : t.textContent = n.label, le(t), "parent" in n ? e.bus.fire("operation", {
      name: "finishEditSummary",
      obj: n
    }) : e.bus.fire("operation", {
      name: "finishEditArrowLabel",
      obj: n
    }));
  });
}, Rn = function(e) {
  const t = this.map.querySelector("me-root"), n = t.offsetTop, o = t.offsetLeft, s = t.offsetWidth, i = t.offsetHeight, l = this.map.querySelectorAll("me-main > me-wrapper");
  this.lines.innerHTML = "";
  for (let c = 0; c < l.length; c++) {
    const r = l[c], a = r.querySelector("me-tpc"), { offsetLeft: d, offsetTop: h } = A(this.nodes, a), u = a.offsetWidth, p = a.offsetHeight, v = r.parentNode.className, m = this.generateMainBranch({ pT: n, pL: o, pW: s, pH: i, cT: h, cL: d, cW: u, cH: p, direction: v, containerHeight: this.nodes.offsetHeight }), y = this.theme.palette, g = a.nodeObj.branchColor || y[c % y.length];
    if (a.style.borderColor = g, this.lines.appendChild(it(m, g, "3")), e && e !== r)
      continue;
    const x = q("subLines"), E = r.lastChild;
    E.tagName === "svg" && E.remove(), r.appendChild(x), lt(this, x, g, r, v, !0);
  }
  this.labelContainer.innerHTML = "", this.renderArrow(), this.renderSummary(), this.bus.fire("linkDiv");
}, lt = function(e, t, n, o, s, i) {
  const l = o.firstChild, c = o.children[1].children;
  if (c.length === 0) return;
  const r = l.offsetTop, a = l.offsetLeft, d = l.offsetWidth, h = l.offsetHeight;
  for (let u = 0; u < c.length; u++) {
    const p = c[u], v = p.firstChild, m = v.offsetTop, y = v.offsetLeft, g = v.offsetWidth, x = v.offsetHeight, E = v.firstChild.nodeObj.branchColor || n, N = e.generateSubBranch({ pT: r, pL: a, pW: d, pH: h, cT: m, cL: y, cW: g, cH: x, direction: s, isFirst: i });
    t.appendChild(it(N, E, "2"));
    const f = v.children[1];
    if (f) {
      if (!f.expanded) continue;
    } else
      continue;
    lt(e, t, E, p, s);
  }
}, Bn = {
  addChild: "Add child",
  addParent: "Add parent",
  addSibling: "Add sibling",
  removeNode: "Remove node",
  focus: "Focus Mode",
  cancelFocus: "Cancel Focus Mode",
  moveUp: "Move up",
  moveDown: "Move down",
  link: "Link",
  linkBidirectional: "Bidirectional Link",
  clickTips: "Please click the target node",
  summary: "Summary"
};
function Wn(e, t) {
  const n = {
    focus: !0,
    link: !0,
    locale: Bn
  };
  t = t === !0 ? n : Object.assign(n, t);
  const o = (b) => {
    const w = document.createElement("div");
    return w.innerText = b, w.className = "tips", w;
  }, s = (b, w, S) => {
    const C = document.createElement("li");
    return C.id = b, C.innerHTML = `<span>${de(w)}</span><span ${S ? 'class="key"' : ""}>${de(S)}</span>`, C;
  }, i = t.locale, l = s("cm-add_child", i.addChild, "Tab"), c = s("cm-add_parent", i.addParent, "Ctrl + Enter"), r = s("cm-add_sibling", i.addSibling, "Enter"), a = s("cm-remove_child", i.removeNode, "Delete"), d = s("cm-fucus", i.focus, ""), h = s("cm-unfucus", i.cancelFocus, ""), u = s("cm-up", i.moveUp, "PgUp"), p = s("cm-down", i.moveDown, "Pgdn"), v = s("cm-link", i.link, ""), m = s("cm-link-bidirectional", i.linkBidirectional, ""), y = s("cm-summary", i.summary, ""), g = document.createElement("ul");
  if (g.className = "menu-list", g.appendChild(l), g.appendChild(c), g.appendChild(r), g.appendChild(a), t.focus && (g.appendChild(d), g.appendChild(h)), g.appendChild(u), g.appendChild(p), g.appendChild(y), t.link && (g.appendChild(v), g.appendChild(m)), t && t.extend)
    for (let b = 0; b < t.extend.length; b++) {
      const w = t.extend[b], S = s(w.name, w.name, w.key || "");
      g.appendChild(S), S.onclick = (C) => {
        w.onclick(C);
      };
    }
  const x = document.createElement("div");
  x.className = "context-menu", x.appendChild(g), x.hidden = !0, e.container.append(x);
  let E = !0;
  const N = (b) => {
    const w = b.target;
    if (ne(w)) {
      w.parentElement.tagName === "ME-ROOT" ? E = !0 : E = !1, E ? (d.className = "disabled", u.className = "disabled", p.className = "disabled", c.className = "disabled", r.className = "disabled", a.className = "disabled") : (d.className = "", u.className = "", p.className = "", c.className = "", r.className = "", a.className = ""), x.hidden = !1, g.style.top = "", g.style.bottom = "", g.style.left = "", g.style.right = "";
      const S = g.offsetHeight, C = g.offsetWidth, T = g.getBoundingClientRect(), D = b.clientY - T.top, L = b.clientX - T.left;
      S + D > window.innerHeight ? (g.style.top = "", g.style.bottom = "0px") : (g.style.bottom = "", g.style.top = D + 15 + "px"), C + L > window.innerWidth ? (g.style.left = "", g.style.right = "0px") : (g.style.right = "", g.style.left = L + 10 + "px");
    }
  };
  e.bus.addListener("showContextMenu", N), x.onclick = (b) => {
    b.target === x && (x.hidden = !0);
  }, l.onclick = () => {
    e.addChild(), x.hidden = !0;
  }, c.onclick = () => {
    e.insertParent(), x.hidden = !0;
  }, r.onclick = () => {
    E || (e.insertSibling("after"), x.hidden = !0);
  }, a.onclick = () => {
    E || (e.removeNodes(e.currentNodes || []), x.hidden = !0);
  }, d.onclick = () => {
    E || (e.focusNode(e.currentNode), x.hidden = !0);
  }, h.onclick = () => {
    e.cancelFocus(), x.hidden = !0;
  }, u.onclick = () => {
    E || (e.moveUpNode(), x.hidden = !0);
  }, p.onclick = () => {
    E || (e.moveDownNode(), x.hidden = !0);
  };
  const f = (b) => {
    x.hidden = !0;
    const w = e.currentNode, S = o(i.clickTips);
    e.container.appendChild(S), e.map.addEventListener(
      "click",
      (C) => {
        C.preventDefault(), S.remove();
        const T = C.target;
        (T.parentElement.tagName === "ME-PARENT" || T.parentElement.tagName === "ME-ROOT") && e.createArrow(w, T, b);
      },
      {
        once: !0
      }
    );
  };
  return v.onclick = () => f(), m.onclick = () => f({ bidirectional: !0 }), y.onclick = () => {
    x.hidden = !0, e.createSummary(), e.unselectNodes(e.currentNodes);
  }, () => {
    l.onclick = null, c.onclick = null, r.onclick = null, a.onclick = null, d.onclick = null, h.onclick = null, u.onclick = null, p.onclick = null, v.onclick = null, y.onclick = null, x.onclick = null, e.container.oncontextmenu = null;
  };
}
const Yn = function(e) {
  return ["createSummary", "removeSummary", "finishEditSummary"].includes(e.name) ? {
    type: "summary",
    value: e.obj.id
  } : ["createArrow", "removeArrow", "finishEditArrowLabel"].includes(e.name) ? {
    type: "arrow",
    value: e.obj.id
  } : ["removeNodes", "copyNodes", "moveNodeBefore", "moveNodeAfter", "moveNodeIn"].includes(e.name) ? {
    type: "nodes",
    value: e.objs.map((t) => t.id)
  } : {
    type: "nodes",
    value: [e.obj.id]
  };
};
function Xn(e) {
  let t = [], n = -1, o = e.getData(), s = [];
  e.undo = function() {
    if (n > -1) {
      const r = t[n];
      o = r.prev, e.refresh(r.prev);
      try {
        r.currentTarget.type === "nodes" && (r.operation === "removeNodes" ? e.selectNodes(r.currentTarget.value.map((a) => this.findEle(a))) : e.selectNodes(r.currentSelected.map((a) => this.findEle(a))));
      } catch {
      } finally {
        n--;
      }
    }
  }, e.redo = function() {
    if (n < t.length - 1) {
      n++;
      const r = t[n];
      o = r.next, e.refresh(r.next);
      try {
        r.currentTarget.type === "nodes" && (r.operation === "removeNodes" ? e.selectNodes(r.currentSelected.map((a) => this.findEle(a))) : e.selectNodes(r.currentTarget.value.map((a) => this.findEle(a))));
      } catch {
      }
    }
  }, e.clearHistory = function() {
    t = [], n = -1, o = e.getData(), e.clearSelection();
  };
  const i = function(r) {
    if (r.name === "beginEdit") return;
    t = t.slice(0, n + 1);
    const a = e.getData(), d = {
      prev: o,
      operation: r.name,
      currentSelected: s.map((h) => h.id),
      currentTarget: Yn(r),
      next: a
    };
    t.push(d), o = a, n = t.length - 1;
  }, l = function(r) {
    (r.metaKey || r.ctrlKey) && (r.shiftKey && r.key === "Z" || r.key === "y") ? e.redo() : (r.metaKey || r.ctrlKey) && r.key === "z" && e.undo();
  }, c = function() {
    s = e.currentNodes.map((r) => r.nodeObj);
  };
  return e.bus.addListener("operation", i), e.bus.addListener("selectNodes", c), e.container.addEventListener("keydown", l), () => {
    e.bus.removeListener("operation", i), e.bus.removeListener("selectNodes", c), e.container.removeEventListener("keydown", l);
  };
}
const Fn = '<?xml version="1.0" standalone="no"?><!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd"><svg t="1750169394918" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="2021" xmlns:xlink="http://www.w3.org/1999/xlink" width="200" height="200"><path d="M851.91168 328.45312c-59.97056 0-108.6208 48.47104-108.91264 108.36992l-137.92768 38.4a109.14304 109.14304 0 0 0-63.46752-46.58688l1.39264-137.11872c47.29344-11.86816 82.31936-54.66624 82.31936-105.64096 0-60.15488-48.76288-108.91776-108.91776-108.91776s-108.91776 48.76288-108.91776 108.91776c0 49.18784 32.60928 90.75712 77.38368 104.27392l-1.41312 138.87488a109.19936 109.19936 0 0 0-63.50336 48.55808l-138.93632-39.48544 0.01024-0.72704c0-60.15488-48.76288-108.91776-108.91776-108.91776s-108.91776 48.75776-108.91776 108.91776c0 60.15488 48.76288 108.91264 108.91776 108.91264 39.3984 0 73.91232-20.92032 93.03552-52.2496l139.19232 39.552-0.00512 0.2304c0 25.8304 9.00096 49.5616 24.02816 68.23424l-90.14272 132.63872a108.7488 108.7488 0 0 0-34.2528-5.504c-60.15488 0-108.91776 48.768-108.91776 108.91776 0 60.16 48.76288 108.91776 108.91776 108.91776 60.16 0 108.92288-48.75776 108.92288-108.91776 0-27.14624-9.9328-51.968-26.36288-71.04l89.04704-131.03104a108.544 108.544 0 0 0 37.6832 6.70208 108.672 108.672 0 0 0 36.48512-6.272l93.13792 132.57216a108.48256 108.48256 0 0 0-24.69888 69.0688c0 60.16 48.768 108.92288 108.91776 108.92288 60.16 0 108.91776-48.76288 108.91776-108.92288 0-60.14976-48.75776-108.91776-108.91776-108.91776a108.80512 108.80512 0 0 0-36.69504 6.3488l-93.07136-132.48a108.48768 108.48768 0 0 0 24.79616-72.22784l136.09984-37.888c18.99008 31.93856 53.84192 53.3504 93.69088 53.3504 60.16 0 108.92288-48.75776 108.92288-108.91264-0.00512-60.15488-48.77312-108.92288-108.92288-108.92288z" p-id="2022"></path></svg>', Kn = '<?xml version="1.0" standalone="no"?><!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd"><svg t="1750169375313" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="1775" xmlns:xlink="http://www.w3.org/1999/xlink" width="200" height="200"><path d="M639 463.30000001L639 285.1c0-36.90000001-26.4-68.5-61.3-68.5l-150.2 0c-1.5 0-3 0.1-4.5 0.3-10.2-38.7-45.5-67.3-87.5-67.3-50 0-90.5 40.5-90.5 90.5s40.5 90.5 90.5 90.5c42 0 77.3-28.6 87.5-67.39999999 1.4 0.3 2.9 0.4 4.5 0.39999999L577.7 263.6c6.8 0 14.3 8.9 14.3 21.49999999l0 427.00000001c0 12.7-7.40000001 21.5-14.30000001 21.5l-150.19999999 0c-1.5 0-3 0.2-4.5 0.4-10.2-38.8-45.5-67.3-87.5-67.3-50 0-90.5 40.5-90.5 90.4 0 49.9 40.5 90.6 90.5 90.59999999 42 0 77.3-28.6 87.5-67.39999999 1.4 0.2 2.9 0.4 4.49999999 0.4L577.7 780.7c34.80000001 0 61.3-31.6 61.3-68.50000001L639 510.3l79.1 0c10.4 38.5 45.49999999 67 87.4 67 50 0 90.5-40.5 90.5-90.5s-40.5-90.5-90.5-90.5c-41.79999999 0-77.00000001 28.4-87.4 67L639 463.30000001z" fill="currentColor" p-id="1776"></path></svg>', Vn = '<?xml version="1.0" standalone="no"?><!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd"><svg t="1750169667709" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="3037" xmlns:xlink="http://www.w3.org/1999/xlink" width="200" height="200"><path d="M385 560.69999999L385 738.9c0 36.90000001 26.4 68.5 61.3 68.5l150.2 0c1.5 0 3-0.1 4.5-0.3 10.2 38.7 45.5 67.3 87.5 67.3 50 0 90.5-40.5 90.5-90.5s-40.5-90.5-90.5-90.5c-42 0-77.3 28.6-87.5 67.39999999-1.4-0.3-2.9-0.4-4.5-0.39999999L446.3 760.4c-6.8 0-14.3-8.9-14.3-21.49999999l0-427.00000001c0-12.7 7.40000001-21.5 14.30000001-21.5l150.19999999 0c1.5 0 3-0.2 4.5-0.4 10.2 38.8 45.5 67.3 87.5 67.3 50 0 90.5-40.5 90.5-90.4 0-49.9-40.5-90.6-90.5-90.59999999-42 0-77.3 28.6-87.5 67.39999999-1.4-0.2-2.9-0.4-4.49999999-0.4L446.3 243.3c-34.80000001 0-61.3 31.6-61.3 68.50000001L385 513.7l-79.1 0c-10.4-38.5-45.49999999-67-87.4-67-50 0-90.5 40.5-90.5 90.5s40.5 90.5 90.5 90.5c41.79999999 0 77.00000001-28.4 87.4-67L385 560.69999999z" fill="currentColor" p-id="3038"></path></svg>', zn = '<?xml version="1.0" standalone="no"?><!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd"><svg t="1750169402629" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="2170" xmlns:xlink="http://www.w3.org/1999/xlink" width="200" height="200"><path d="M639.328 416c8.032 0 16.096-3.008 22.304-9.056l202.624-197.184-0.8 143.808c-0.096 17.696 14.144 32.096 31.808 32.192 0.064 0 0.128 0 0.192 0 17.6 0 31.904-14.208 32-31.808l1.248-222.208c0-0.672-0.352-1.248-0.384-1.92 0.032-0.512 0.288-0.896 0.288-1.408 0.032-17.664-14.272-32-31.968-32.032L671.552 96l-0.032 0c-17.664 0-31.968 14.304-32 31.968C639.488 145.632 653.824 160 671.488 160l151.872 0.224-206.368 200.8c-12.672 12.32-12.928 32.608-0.64 45.248C622.656 412.736 630.976 416 639.328 416z" p-id="2171"></path><path d="M896.032 639.552 896.032 639.552c-17.696 0-32 14.304-32.032 31.968l-0.224 151.872-200.832-206.4c-12.32-12.64-32.576-12.96-45.248-0.64-12.672 12.352-12.928 32.608-0.64 45.248l197.184 202.624-143.808-0.8c-0.064 0-0.128 0-0.192 0-17.6 0-31.904 14.208-32 31.808-0.096 17.696 14.144 32.096 31.808 32.192l222.24 1.248c0.064 0 0.128 0 0.192 0 0.64 0 1.12-0.32 1.76-0.352 0.512 0.032 0.896 0.288 1.408 0.288l0.032 0c17.664 0 31.968-14.304 32-31.968L928 671.584C928.032 653.952 913.728 639.584 896.032 639.552z" p-id="2172"></path><path d="M209.76 159.744l143.808 0.8c0.064 0 0.128 0 0.192 0 17.6 0 31.904-14.208 32-31.808 0.096-17.696-14.144-32.096-31.808-32.192L131.68 95.328c-0.064 0-0.128 0-0.192 0-0.672 0-1.248 0.352-1.888 0.384-0.448 0-0.8-0.256-1.248-0.256 0 0-0.032 0-0.032 0-17.664 0-31.968 14.304-32 31.968L96 352.448c-0.032 17.664 14.272 32 31.968 32.032 0 0 0.032 0 0.032 0 17.664 0 31.968-14.304 32-31.968l0.224-151.936 200.832 206.4c6.272 6.464 14.624 9.696 22.944 9.696 8.032 0 16.096-3.008 22.304-9.056 12.672-12.32 12.96-32.608 0.64-45.248L209.76 159.744z" p-id="2173"></path><path d="M362.368 617.056l-202.624 197.184 0.8-143.808c0.096-17.696-14.144-32.096-31.808-32.192-0.064 0-0.128 0-0.192 0-17.6 0-31.904 14.208-32 31.808l-1.248 222.24c0 0.704 0.352 1.312 0.384 2.016 0 0.448-0.256 0.832-0.256 1.312-0.032 17.664 14.272 32 31.968 32.032L352.448 928c0 0 0.032 0 0.032 0 17.664 0 31.968-14.304 32-31.968s-14.272-32-31.968-32.032l-151.936-0.224 206.4-200.832c12.672-12.352 12.96-32.608 0.64-45.248S375.008 604.704 362.368 617.056z" p-id="2174"></path></svg>', Gn = '<?xml version="1.0" standalone="no"?><!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd"><svg t="1750169573443" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="2883" xmlns:xlink="http://www.w3.org/1999/xlink" width="200" height="200"><path d="M514.133333 488.533333m-106.666666 0a106.666667 106.666667 0 1 0 213.333333 0 106.666667 106.666667 0 1 0-213.333333 0Z" fill="currentColor" p-id="2884"></path><path d="M512 64C264.533333 64 64 264.533333 64 512c0 236.8 183.466667 428.8 416 445.866667v-134.4c-53.333333-59.733333-200.533333-230.4-200.533333-334.933334 0-130.133333 104.533333-234.666667 234.666666-234.666666s234.666667 104.533333 234.666667 234.666666c0 61.866667-49.066667 153.6-145.066667 270.933334l-59.733333 68.266666V960C776.533333 942.933333 960 748.8 960 512c0-247.466667-200.533333-448-448-448z" fill="currentColor" p-id="2885"></path></svg>', qn = '<?xml version="1.0" standalone="no"?><!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd"><svg t="1750169419447" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="2480" xmlns:xlink="http://www.w3.org/1999/xlink" width="200" height="200"><path d="M863.328 482.56l-317.344-1.12L545.984 162.816c0-17.664-14.336-32-32-32s-32 14.336-32 32l0 318.4L159.616 480.064c-0.032 0-0.064 0-0.096 0-17.632 0-31.936 14.24-32 31.904C127.424 529.632 141.728 544 159.392 544.064l322.592 1.152 0 319.168c0 17.696 14.336 32 32 32s32-14.304 32-32l0-318.944 317.088 1.12c0.064 0 0.096 0 0.128 0 17.632 0 31.936-14.24 32-31.904C895.264 496.992 880.96 482.624 863.328 482.56z" p-id="2481"></path></svg>', Un = '<?xml version="1.0" standalone="no"?><!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd"><svg t="1750169426515" class="icon" viewBox="0 0 1024 1024" version="1.1" xmlns="http://www.w3.org/2000/svg" p-id="2730" xmlns:xlink="http://www.w3.org/1999/xlink" width="200" height="200"><path d="M863.744 544 163.424 544c-17.664 0-32-14.336-32-32s14.336-32 32-32l700.32 0c17.696 0 32 14.336 32 32S881.44 544 863.744 544z" p-id="2731"></path></svg>', Jn = {
  side: Fn,
  left: Kn,
  right: Vn,
  full: zn,
  living: Gn,
  zoomin: qn,
  zoomout: Un
}, R = (e, t) => {
  const n = document.createElement("span");
  return n.id = e, n.innerHTML = Jn[t], n;
};
function Zn(e) {
  const t = document.createElement("div"), n = R("fullscreen", "full"), o = R("toCenter", "living"), s = R("zoomout", "zoomout"), i = R("zoomin", "zoomin");
  t.appendChild(n), t.appendChild(o), t.appendChild(s), t.appendChild(i), t.className = "mind-elixir-toolbar rb";
  let l = null;
  const c = () => {
    const a = e.container.getBoundingClientRect(), d = be(e.map.style.transform), h = a.width / 2, u = a.height / 2, p = (h - d.x) / e.scaleVal, v = (u - d.y) / e.scaleVal;
    l = {
      containerRect: a,
      currentTransform: d,
      mapCenterX: p,
      mapCenterY: v
    };
  }, r = () => {
    if (l) {
      const a = e.container.getBoundingClientRect(), d = a.width / 2, h = a.height / 2, u = d - l.mapCenterX * e.scaleVal, p = h - l.mapCenterY * e.scaleVal, v = u - l.currentTransform.x, m = p - l.currentTransform.y;
      e.move(v, m);
    }
  };
  return e.el.addEventListener("fullscreenchange", r), n.onclick = () => {
    c(), document.fullscreenElement !== e.el ? e.el.requestFullscreen() : document.exitFullscreen();
  }, o.onclick = () => {
    e.toCenter();
  }, s.onclick = () => {
    e.scale(e.scaleVal - e.scaleSensitivity);
  }, i.onclick = () => {
    e.scale(e.scaleVal + e.scaleSensitivity);
  }, t;
}
function Qn(e) {
  const t = document.createElement("div"), n = R("tbltl", "left"), o = R("tbltr", "right"), s = R("tblts", "side");
  return t.appendChild(n), t.appendChild(o), t.appendChild(s), t.className = "mind-elixir-toolbar lt", n.onclick = () => {
    e.initLeft();
  }, o.onclick = () => {
    e.initRight();
  }, s.onclick = () => {
    e.initSide();
  }, t;
}
function eo(e) {
  e.container.append(Zn(e)), e.container.append(Qn(e));
}
class to {
  _listeners = /* @__PURE__ */ new Map();
  addEventListener(t, n) {
    const o = this._listeners.get(t) ?? /* @__PURE__ */ new Set();
    return this._listeners.set(t, o), o.add(n), this;
  }
  removeEventListener(t, n) {
    return this._listeners.get(t)?.delete(n), this;
  }
  dispatchEvent(t, ...n) {
    let o = !0;
    for (const s of this._listeners.get(t) ?? [])
      o = s(...n) !== !1 && o;
    return o;
  }
  unbindAllListeners() {
    this._listeners.clear();
  }
  // Let's also support on, off and emit like node
  on = this.addEventListener;
  off = this.removeEventListener;
  emit = this.dispatchEvent;
}
const Re = (e, t = "px") => typeof e == "number" ? e + t : e, H = ({ style: e }, t, n) => {
  if (typeof t == "object")
    for (const [o, s] of Object.entries(t))
      s !== void 0 && (e[o] = Re(s));
  else n !== void 0 && (e[t] = Re(n));
}, Be = (e = 0, t = 0, n = 0, o = 0) => {
  const s = { x: e, y: t, width: n, height: o, top: t, left: e, right: e + n, bottom: t + o };
  return { ...s, toJSON: () => JSON.stringify(s) };
}, no = (e) => {
  let t, n = -1, o = !1;
  return {
    next: (...s) => {
      t = s, o || (o = !0, n = requestAnimationFrame(() => {
        e(...t), o = !1;
      }));
    },
    cancel: () => {
      cancelAnimationFrame(n), o = !1;
    }
  };
}, We = (e, t, n = "touch") => {
  switch (n) {
    case "center": {
      const o = t.left + t.width / 2, s = t.top + t.height / 2;
      return o >= e.left && o <= e.right && s >= e.top && s <= e.bottom;
    }
    case "cover":
      return t.left >= e.left && t.top >= e.top && t.right <= e.right && t.bottom <= e.bottom;
    case "touch":
      return e.right >= t.left && e.left <= t.right && e.bottom >= t.top && e.top <= t.bottom;
  }
}, oo = () => matchMedia("(hover: none), (pointer: coarse)").matches, so = () => "safari" in window, fe = (e) => Array.isArray(e) ? e : [e], ct = (e) => (t, n, o, s = {}) => {
  (t instanceof HTMLCollection || t instanceof NodeList) && (t = Array.from(t)), n = fe(n), t = fe(t);
  for (const i of t)
    if (i)
      for (const l of n)
        i[e](l, o, { capture: !1, ...s });
}, Y = ct("addEventListener"), O = ct("removeEventListener"), Q = (e) => {
  const { clientX: t, clientY: n, target: o } = e.touches?.[0] ?? e;
  return { x: t, y: n, target: o };
}, X = (e, t = document) => fe(e).map((n) => typeof n == "string" ? Array.from(t.querySelectorAll(n)) : n instanceof Element ? n : null).flat().filter(Boolean), io = (e, t) => t.some((n) => typeof n == "number" ? e.button === n : typeof n == "object" ? n.button !== e.button ? !1 : n.modifiers.every((o) => {
  switch (o) {
    case "alt":
      return e.altKey;
    case "ctrl":
      return e.ctrlKey || e.metaKey;
    case "shift":
      return e.shiftKey;
  }
}) : !1), { abs: I, max: Ye, min: Xe, ceil: Fe } = Math, Ke = (e = []) => ({
  stored: e,
  selected: [],
  touched: [],
  changed: { added: [], removed: [] }
});
class ro extends to {
  static version = "mind-elixir-fork";
  // Options
  _options;
  // Selection store
  _selection = Ke();
  // Area element and clipping element
  _area;
  _clippingElement;
  // Target container (element) and boundary (cached)
  _targetElement;
  _targetBoundary;
  _targetBoundaryScrolled = !0;
  _targetRect;
  _selectables = [];
  _latestElement;
  // Dynamically constructed area rect
  _areaLocation = { y1: 0, x2: 0, y2: 0, x1: 0 };
  _areaRect = Be();
  // If a single click is being performed, it's a single-click until the user dragged the mouse
  _singleClick = !0;
  _frame;
  // Required data for scrolling
  _scrollAvailable = !0;
  _scrollingActive = !1;
  _scrollSpeed = { x: 0, y: 0 };
  _scrollDelta = { x: 0, y: 0 };
  constructor(t) {
    super(), this._options = {
      selectionAreaClass: "selection-area",
      selectionContainerClass: void 0,
      selectables: [],
      document: window.document,
      startAreas: ["html"],
      boundaries: ["html"],
      container: "body",
      mindElixirInstance: void 0,
      // 添加默认值
      ...t,
      behaviour: {
        overlap: "invert",
        intersect: "touch",
        triggers: [0],
        ...t.behaviour,
        startThreshold: t.behaviour?.startThreshold ? typeof t.behaviour.startThreshold == "number" ? t.behaviour.startThreshold : { x: 10, y: 10, ...t.behaviour.startThreshold } : { x: 10, y: 10 },
        scrolling: {
          speedDivider: 10,
          ...t.behaviour?.scrolling,
          startScrollMargins: {
            x: 0,
            y: 0,
            ...t.behaviour?.scrolling?.startScrollMargins
          }
        }
      },
      features: {
        range: !0,
        touch: !0,
        deselectOnBlur: !1,
        ...t.features,
        singleTap: {
          allow: !0,
          intersect: "native",
          ...t.features?.singleTap
        }
      }
    };
    for (const i of Object.getOwnPropertyNames(Object.getPrototypeOf(this)))
      typeof this[i] == "function" && (this[i] = this[i].bind(this));
    const { document: n, selectionAreaClass: o, selectionContainerClass: s } = this._options;
    this._area = n.createElement("div"), this._clippingElement = n.createElement("div"), this._clippingElement.appendChild(this._area), this._area.classList.add(o), s && this._clippingElement.classList.add(s), H(this._area, {
      willChange: "top, left, bottom, right, width, height",
      top: 0,
      left: 0,
      position: "fixed"
    }), H(this._clippingElement, {
      overflow: "hidden",
      position: "fixed",
      transform: "translate3d(0, 0, 0)",
      // https://stackoverflow.com/a/38268846
      pointerEvents: "none",
      zIndex: "1"
    }), this._frame = no((i) => {
      this._recalculateSelectionAreaRect(), this._updateElementSelection(), this._emitEvent("move", i), this._redrawSelectionArea();
    }), this.enable();
  }
  _toggleStartEvents(t = !0) {
    const { document: n } = this._options;
    (t ? Y : O)(n, "pointerdown", this._onTapStart);
  }
  _onTapStart(t, n = !1) {
    const { x: o, y: s, target: i } = Q(t), { document: l, startAreas: c, boundaries: r, behaviour: a, features: d } = this._options, h = i.getBoundingClientRect();
    if (!io(t, a.triggers))
      return;
    const u = X(c, l), p = X(r, l);
    this._targetElement = p.find((g) => We(g.getBoundingClientRect(), h));
    const v = t.composedPath(), m = u.find((g) => v.includes(g));
    if (this._targetBoundary = p.find((g) => v.includes(g)), !this._targetElement || !m || !this._targetBoundary || !n && this._emitEvent("beforestart", t) === !1)
      return;
    this._areaLocation = { x1: o, y1: s, x2: 0, y2: 0 };
    const y = l.scrollingElement ?? l.body;
    this._scrollDelta = { x: y.scrollLeft, y: y.scrollTop }, this._singleClick = !0, this.clearSelection(!1, !0), Y(l, ["pointermove"], this._delayedTapMove, { passive: !1 }), Y(l, ["pointerup", "pointercancel"], this._onTapStop), Y(l, "scroll", this._onScroll), d.deselectOnBlur && (this._targetBoundaryScrolled = !1, Y(this._targetBoundary, "scroll", this._onStartAreaScroll));
  }
  _onSingleTap(t) {
    const {
      singleTap: { intersect: n },
      range: o
    } = this._options.features, s = Q(t);
    let i;
    if (n === "native")
      i = s.target;
    else if (n === "touch") {
      this.resolveSelectables();
      const { x: c, y: r } = s;
      i = this._selectables.find((a) => {
        const { right: d, left: h, top: u, bottom: p } = a.getBoundingClientRect();
        return c < d && c > h && r < p && r > u;
      });
    }
    if (!i)
      return;
    for (this.resolveSelectables(); !this._selectables.includes(i); )
      if (i.parentElement)
        i = i.parentElement;
      else {
        this._targetBoundaryScrolled || this.clearSelection();
        return;
      }
    const { stored: l } = this._selection;
    if (this._emitEvent("start", t), t.shiftKey && o && this._latestElement) {
      const c = this._latestElement, [r, a] = c.compareDocumentPosition(i) & 4 ? [i, c] : [c, i], d = [
        ...this._selectables.filter((h) => h.compareDocumentPosition(r) & 4 && h.compareDocumentPosition(a) & 2),
        r,
        a
      ];
      this.select(d), this._latestElement = c;
    } else l.includes(i) && (l.length === 1 || t.ctrlKey || l.every((c) => this._selection.stored.includes(c))) ? this.deselect(i) : (this.select(i), this._latestElement = i);
  }
  _delayedTapMove(t) {
    const {
      container: n,
      document: o,
      behaviour: { startThreshold: s }
    } = this._options, { x1: i, y1: l } = this._areaLocation, { x: c, y: r } = Q(t);
    if (
      // Single number for both coordinates
      typeof s == "number" && I(c + r - (i + l)) >= s || // Different x and y threshold
      typeof s == "object" && I(c - i) >= s.x || I(r - l) >= s.y
    ) {
      if (O(o, ["pointermove"], this._delayedTapMove, { passive: !1 }), this._emitEvent("beforedrag", t) === !1) {
        O(o, ["pointerup", "pointercancel"], this._onTapStop);
        return;
      }
      Y(o, ["pointermove"], this._onTapMove, { passive: !1 }), H(this._area, "display", "block"), X(n, o)[0].appendChild(this._clippingElement), this.resolveSelectables(), this._singleClick = !1, this._targetRect = this._targetElement.getBoundingClientRect(), this._scrollAvailable = this._targetElement.scrollHeight !== this._targetElement.clientHeight || this._targetElement.scrollWidth !== this._targetElement.clientWidth, this._scrollAvailable && (this._selectables = this._selectables.filter((a) => this._targetElement.contains(a))), this._setupSelectionArea(), this._emitEvent("start", t), this._onTapMove(t);
    }
    this._handleMoveEvent(t);
  }
  _setupSelectionArea() {
    const { _clippingElement: t, _targetElement: n, _area: o } = this, s = this._targetRect = n.getBoundingClientRect();
    this._scrollAvailable ? (H(t, {
      top: s.top,
      left: s.left,
      width: s.width,
      height: s.height
    }), H(o, {
      marginTop: -s.top,
      marginLeft: -s.left
    })) : (H(t, {
      top: 0,
      left: 0,
      width: "100%",
      height: "100%"
    }), H(o, {
      marginTop: 0,
      marginLeft: 0
    }));
  }
  _onTapMove(t) {
    const { _scrollSpeed: n, _areaLocation: o, _options: s, _frame: i } = this, { speedDivider: l } = s.behaviour.scrolling, { x: c, y: r } = Q(t);
    if (o.x2 = c, o.y2 = r, this._scrollAvailable && !this._scrollingActive && (n.y || n.x)) {
      this._scrollingActive = !0;
      const a = () => {
        if (!n.x && !n.y) {
          this._scrollingActive = !1;
          return;
        }
        const d = this._options.mindElixirInstance;
        if (d && d.move) {
          const h = n.x ? Fe(n.x / l) : 0, u = n.y ? Fe(n.y / l) : 0;
          (h || u) && (d.move(-h, -u), o.x1 -= h, o.y1 -= u);
        }
        i.next(t), requestAnimationFrame(a);
      };
      requestAnimationFrame(a);
    } else
      i.next(t);
    this._handleMoveEvent(t);
  }
  _handleMoveEvent(t) {
    const { features: n } = this._options;
    (n.touch && oo() || this._scrollAvailable && so()) && t.preventDefault();
  }
  _onScroll() {
    const {
      _scrollDelta: t,
      _options: { document: n }
    } = this, { scrollTop: o, scrollLeft: s } = n.scrollingElement ?? n.body;
    this._areaLocation.x1 += t.x - s, this._areaLocation.y1 += t.y - o, t.x = s, t.y = o, this._setupSelectionArea(), this._frame.next(null);
  }
  _onStartAreaScroll() {
    this._targetBoundaryScrolled = !0, O(this._targetElement, "scroll", this._onStartAreaScroll);
  }
  _recalculateSelectionAreaRect() {
    const { _scrollSpeed: t, _areaLocation: n, _targetElement: o, _options: s } = this, i = this._targetRect, { x1: l, y1: c } = n;
    let { x2: r, y2: a } = n;
    const {
      behaviour: {
        scrolling: { startScrollMargins: d }
      }
    } = s;
    r < i.left + d.x ? (t.x = -I(i.left - r + d.x), r = r < i.left ? i.left : r) : r > i.right - d.x ? (t.x = I(i.left + i.width - r - d.x), r = r > i.right ? i.right : r) : t.x = 0, a < i.top + d.y ? (t.y = -I(i.top - a + d.y), a = a < i.top ? i.top : a) : a > i.bottom - d.y ? (t.y = I(i.top + i.height - a - d.y), a = a > i.bottom ? i.bottom : a) : t.y = 0;
    const h = Xe(l, r), u = Xe(c, a), p = Ye(l, r), v = Ye(c, a);
    this._areaRect = Be(h, u, p - h, v - u);
  }
  _redrawSelectionArea() {
    const { x: t, y: n, width: o, height: s } = this._areaRect, { style: i } = this._area;
    i.left = `${t}px`, i.top = `${n}px`, i.width = `${o}px`, i.height = `${s}px`;
  }
  _onTapStop(t, n) {
    const { document: o, features: s } = this._options, { _singleClick: i } = this;
    O(this._targetElement, "scroll", this._onStartAreaScroll), O(o, ["pointermove"], this._delayedTapMove), O(o, ["pointermove"], this._onTapMove), O(o, ["pointerup", "pointercancel"], this._onTapStop), O(o, "scroll", this._onScroll), this._keepSelection(), t && i && s.singleTap.allow ? this._onSingleTap(t) : !i && !n && (this._updateElementSelection(), this._emitEvent("stop", t)), this._scrollSpeed.x = 0, this._scrollSpeed.y = 0, this._clippingElement.remove(), this._frame?.cancel(), H(this._area, "display", "none");
  }
  _updateElementSelection() {
    const { _selectables: t, _options: n, _selection: o, _areaRect: s } = this, { stored: i, selected: l, touched: c } = o, { intersect: r, overlap: a } = n.behaviour, d = a === "invert", h = [], u = [], p = [];
    for (let m = 0; m < t.length; m++) {
      const y = t[m];
      if (We(s, y.getBoundingClientRect(), r)) {
        if (l.includes(y))
          i.includes(y) && !c.includes(y) && c.push(y);
        else if (d && i.includes(y)) {
          p.push(y);
          continue;
        } else
          u.push(y);
        h.push(y);
      }
    }
    d && u.push(...i.filter((m) => !l.includes(m)));
    const v = a === "keep";
    for (let m = 0; m < l.length; m++) {
      const y = l[m];
      !h.includes(y) && !// Check if the user wants to keep previously selected elements, e.g.,
      // not make them part of the current selection as soon as they're touched.
      (v && i.includes(y)) && p.push(y);
    }
    o.selected = h, o.changed = { added: u, removed: p }, this._latestElement = void 0;
  }
  _emitEvent(t, n) {
    return this.emit(t, {
      event: n,
      store: this._selection,
      selection: this
    });
  }
  _keepSelection() {
    const { _options: t, _selection: n } = this, { selected: o, changed: s, touched: i, stored: l } = n, c = o.filter((r) => !l.includes(r));
    switch (t.behaviour.overlap) {
      case "drop": {
        n.stored = [
          ...c,
          ...l.filter((r) => !i.includes(r))
          // Elements not touched
        ];
        break;
      }
      case "invert": {
        n.stored = [
          ...c,
          ...l.filter((r) => !s.removed.includes(r))
          // Elements not removed from selection
        ];
        break;
      }
      case "keep": {
        n.stored = [
          ...l,
          ...o.filter((r) => !l.includes(r))
          // Newly added
        ];
        break;
      }
    }
  }
  /**
   * Manually triggers the start of a selection
   * @param evt A PointerEvent-like object
   * @param silent If beforestart should be fired
   */
  trigger(t, n = !0) {
    this._onTapStart(t, n);
  }
  /**
   * Can be used if during a selection elements have been added
   * Will update everything that can be selected
   */
  resolveSelectables() {
    this._selectables = X(this._options.selectables, this._options.document);
  }
  /**
   * Same as deselecting, but for all elements currently selected
   * @param includeStored If the store should also get cleared
   * @param quiet If move / stop events should be fired
   */
  clearSelection(t = !0, n = !1) {
    const { selected: o, stored: s, changed: i } = this._selection;
    i.added = [], i.removed.push(...o, ...t ? s : []), n || (this._emitEvent("move", null), this._emitEvent("stop", null)), this._selection = Ke(t ? [] : s);
  }
  /**
   * @returns {Array} Selected elements
   */
  getSelection() {
    return this._selection.stored;
  }
  /**
   * @returns {HTMLElement} The selection area element
   */
  getSelectionArea() {
    return this._area;
  }
  /**
   * @returns {Element[]} Available selectable elements for current selection
   */
  getSelectables() {
    return this._selectables;
  }
  /**
   * Set the location of the selection area
   * @param location A partial AreaLocation object
   */
  setAreaLocation(t) {
    Object.assign(this._areaLocation, t), this._redrawSelectionArea();
  }
  /**
   * @returns {AreaLocation} The current location of the selection area
   */
  getAreaLocation() {
    return this._areaLocation;
  }
  /**
   * Cancel the current selection process, pass true to fire a stop event after cancel
   * @param keepEvent If a stop event should be fired
   */
  cancel(t = !1) {
    this._onTapStop(null, !t);
  }
  /**
   * Unbinds all events and removes the area-element.
   */
  destroy() {
    this.cancel(), this.disable(), this._clippingElement.remove(), super.unbindAllListeners();
  }
  /**
   * Enable selecting elements
   */
  enable = this._toggleStartEvents;
  /**
   * Disable selecting elements
   */
  disable = this._toggleStartEvents.bind(this, !1);
  /**
   * Adds elements to the selection
   * @param query CSS Query, can be an array of queries
   * @param quiet If this should not trigger the move event
   */
  select(t, n = !1) {
    const { changed: o, selected: s, stored: i } = this._selection, l = X(t, this._options.document).filter((c) => !s.includes(c) && !i.includes(c));
    return i.push(...l), s.push(...l), o.added.push(...l), o.removed = [], this._latestElement = void 0, n || (this._emitEvent("move", null), this._emitEvent("stop", null)), l;
  }
  /**
   * Removes a particular element from the selection
   * @param query CSS Query, can be an array of queries
   * @param quiet If this should not trigger the move event
   */
  deselect(t, n = !1) {
    const { selected: o, stored: s, changed: i } = this._selection, l = X(t, this._options.document).filter((c) => o.includes(c) || s.includes(c));
    this._selection.stored = s.filter((c) => !l.includes(c)), this._selection.selected = o.filter((c) => !l.includes(c)), this._selection.changed.added = [], this._selection.changed.removed.push(...l.filter((c) => !i.removed.includes(c))), this._latestElement = void 0, n || (this._emitEvent("move", null), this._emitEvent("stop", null));
  }
}
function lo(e) {
  const t = e.mouseSelectionButton === 2 ? [2] : [0], n = new ro({
    selectables: [".map-container me-tpc"],
    boundaries: [e.container],
    container: e.selectionContainer,
    mindElixirInstance: e,
    // 传递 MindElixir 实例
    features: {
      touch: !1,
      singleTap: {
        allow: !1
      }
    },
    behaviour: {
      triggers: t,
      // Scroll configuration.
      scrolling: {
        // On scrollable areas the number on px per frame is devided by this amount.
        // Default is 10 to provide a enjoyable scroll experience.
        speedDivider: 10,
        startScrollMargins: { x: 50, y: 50 }
      }
    }
  }).on("beforestart", ({ event: o }) => {
    if (!e.editable || e.spacePressed || e.ptState !== 5) return !1;
    const s = o.target;
    if (s.id === "input-box" || s.className === "circle" || s.className !== "map-container")
      return !1;
    !o.ctrlKey && !o.metaKey && e.clearSelection();
    const i = n.getSelectionArea();
    return i.style.background = "#4f90f22d", i.style.border = "1px solid #4f90f2", i.style.borderRadius = "3px", i.parentElement && (i.parentElement.style.zIndex = "9999"), !0;
  }).on(
    "move",
    ({
      store: {
        changed: { added: o, removed: s }
      }
    }) => {
      if (o.length > 0 || s.length > 0, o.length > 0) {
        const i = o.filter((l) => !e.currentNodes?.includes(l));
        if (i.length > 0) {
          for (const l of i)
            l.className = "selected";
          e.currentNodes = [...e.currentNodes || [], ...i], e.bus.fire(
            "selectNodes",
            i.map((l) => l.nodeObj)
          );
        }
      }
      if (s.length > 0) {
        const i = s.filter((l) => e.currentNodes?.includes(l));
        if (i.length > 0) {
          for (const l of i)
            l.classList.remove("selected");
          e.currentNodes = (e.currentNodes || []).filter((l) => !i.includes(l)), e.bus.fire(
            "unselectNodes",
            i.map((l) => l.nodeObj)
          );
        }
      }
    }
  );
  e.selection = n;
}
function at({ pT: e, pL: t, pW: n, pH: o, cT: s, cL: i, cW: l, cH: c, direction: r, containerHeight: a }) {
  let d = t + n / 2;
  const h = e + o / 2;
  let u;
  r === $.LHS ? u = i + l : u = i;
  const p = s + c / 2, m = (1 - Math.abs(p - h) / a) * 0.25 * (n / 2);
  return r === $.LHS ? d = d - n / 10 - m : d = d + n / 10 + m, `M ${d} ${h} Q ${d} ${p} ${u} ${p}`;
}
function dt({ pT: e, pL: t, pW: n, pH: o, cT: s, cL: i, cW: l, cH: c, direction: r, isFirst: a }) {
  const d = parseInt(this.container.style.getPropertyValue("--node-gap-x"));
  let h = 0, u = 0;
  a ? h = e + o / 2 : h = e + o;
  const p = s + c;
  let v = 0, m = 0, y = 0;
  const g = Math.abs(h - p) / 300 * d;
  return r === $.LHS ? (y = t, v = y + d, m = y - d, u = i + d, `M ${v} ${h} C ${y} ${h} ${y + g} ${p} ${m} ${p} H ${u}`) : (y = t + n, v = y - d, m = y + d, u = i + l - d, `M ${v} ${h} C ${y} ${h} ${y - g} ${p} ${m} ${p} H ${u}`);
}
const co = function(e, t = !0) {
  this.theme = e, this.generateMainBranch = this.theme.generateMainBranch || at, this.generateSubBranch = this.theme.generateSubBranch || dt;
  const o = {
    ...(this.theme.type === "dark" ? ge : pe).cssVar,
    ...this.theme.cssVar
  };
  this.compact && (o["--node-gap-x"] = "15px", o["--node-gap-y"] = "2px", o["--main-gap-x"] = "30px", o["--main-gap-y"] = "6px");
  const s = Object.keys(o);
  for (let i = 0; i < s.length; i++) {
    const l = s[i];
    this.container.style.setProperty(l, o[l]);
  }
  t && this.refresh();
}, ao = function(e) {
  this.compact = e, this.theme && this.changeTheme(this.theme);
}, ho = function(e) {
  return {
    dom: e,
    moved: !1,
    // differentiate click and move
    pointerdown: !1,
    lastX: 0,
    lastY: 0,
    handlePointerMove(t) {
      if (this.pointerdown) {
        this.moved = !0;
        const n = t.clientX - this.lastX, o = t.clientY - this.lastY;
        this.lastX = t.clientX, this.lastY = t.clientY, this.cb && this.cb(n, o);
      }
    },
    handlePointerDown(t) {
      t.button === 0 && (this.pointerdown = !0, this.lastX = t.clientX, this.lastY = t.clientY, this.dom.setPointerCapture(t.pointerId));
    },
    handleClear(t) {
      this.pointerdown = !1, t.pointerId !== void 0 && this.dom.releasePointerCapture(t.pointerId);
    },
    cb: null,
    init(t, n) {
      this.cb = n, this.handleClear = this.handleClear.bind(this), this.handlePointerMove = this.handlePointerMove.bind(this), this.handlePointerDown = this.handlePointerDown.bind(this), this.destroy = qe([
        { dom: t, evt: "pointermove", func: this.handlePointerMove },
        { dom: t, evt: "pointerleave", func: this.handleClear },
        { dom: t, evt: "pointerup", func: this.handleClear },
        { dom: this.dom, evt: "pointerdown", func: this.handlePointerDown }
      ]);
    },
    destroy: null,
    clear() {
      this.moved = !1, this.pointerdown = !1;
    }
  };
}, Ve = {
  create: ho
}, ht = "#4dc4ff";
function ft(e, t, n, o, s, i, l, c) {
  return {
    x: e / 8 + n * 3 / 8 + s * 3 / 8 + l / 8,
    y: t / 8 + o * 3 / 8 + i * 3 / 8 + c / 8
  };
}
function fo(e, t, n) {
  e && (e.dataset.x = t.toString(), e.dataset.y = n.toString(), le(e));
}
function F(e, t, n, o, s) {
  k(e, {
    x1: t + "",
    y1: n + "",
    x2: o + "",
    y2: s + ""
  });
}
function ue(e, t, n, o, s, i, l, c, r, a) {
  const d = `M ${t} ${n} C ${o} ${s} ${i} ${l} ${c} ${r}`;
  e.line.setAttribute("d", d);
  const h = a.style || {};
  e.line.setAttribute("stroke", h.stroke || "rgb(227, 125, 116)"), e.line.setAttribute("stroke-width", String(h.strokeWidth || "2")), e.line.setAttribute("stroke-dasharray", h.strokeDasharray || "8,2"), e.line.setAttribute("stroke-linecap", h.strokeLinecap || "cap"), h.opacity !== void 0 && h.opacity !== null && h.opacity !== "" ? e.line.setAttribute("opacity", String(h.opacity)) : e.line.removeAttribute("opacity");
  const u = e.querySelectorAll('path[stroke="transparent"]');
  u.length > 0 && u[0].setAttribute("d", d);
  const p = se(i, l, c, r);
  if (p) {
    const g = `M ${p.x1} ${p.y1} L ${c} ${r} L ${p.x2} ${p.y2}`;
    e.arrow1.setAttribute("d", g), u.length > 1 && u[1].setAttribute("d", g), e.arrow1.setAttribute("stroke", h.stroke || "rgb(227, 125, 116)"), e.arrow1.setAttribute("stroke-width", String(h.strokeWidth || "2")), e.arrow1.setAttribute("stroke-linecap", h.strokeLinecap || "cap"), h.opacity !== void 0 && h.opacity !== null && h.opacity !== "" ? e.arrow1.setAttribute("opacity", String(h.opacity)) : e.arrow1.removeAttribute("opacity");
  }
  if (a.bidirectional) {
    const g = se(o, s, t, n);
    if (g) {
      const x = `M ${g.x1} ${g.y1} L ${t} ${n} L ${g.x2} ${g.y2}`;
      e.arrow2.setAttribute("d", x), u.length > 2 && u[2].setAttribute("d", x);
    }
  } else
    e.arrow2.setAttribute("d", ""), u.length > 2 && u[2].setAttribute("d", "");
  e.arrow2.setAttribute("stroke", h.stroke || "rgb(227, 125, 116)"), e.arrow2.setAttribute("stroke-width", String(h.strokeWidth || "2")), e.arrow2.setAttribute("stroke-linecap", h.strokeLinecap || "cap"), h.opacity !== void 0 && h.opacity !== null && h.opacity !== "" ? e.arrow2.setAttribute("opacity", String(h.opacity)) : e.arrow2.removeAttribute("opacity");
  const { x: v, y: m } = ft(t, n, o, s, i, l, c, r);
  e.labelEl && fo(e.labelEl, v, m);
  const y = e.labelEl;
  y && (y.style.color = h.labelColor || "rgb(235, 95, 82)"), vo(e);
}
function V(e, t, n) {
  const { offsetLeft: o, offsetTop: s } = A(e.nodes, t), i = t.offsetWidth, l = t.offsetHeight, c = o + i / 2, r = s + l / 2, a = c + n.x, d = r + n.y;
  return {
    w: i,
    h: l,
    cx: c,
    cy: r,
    ctrlX: a,
    ctrlY: d
  };
}
function j(e) {
  let t, n;
  const o = (e.cy - e.ctrlY) / (e.ctrlX - e.cx);
  return o > e.h / e.w || o < -e.h / e.w ? e.cy - e.ctrlY < 0 ? (t = e.cx - e.h / 2 / o, n = e.cy + e.h / 2) : (t = e.cx + e.h / 2 / o, n = e.cy - e.h / 2) : e.cx - e.ctrlX < 0 ? (t = e.cx + e.w / 2, n = e.cy - e.w * o / 2) : (t = e.cx - e.w / 2, n = e.cy + e.w * o / 2), {
    x: t,
    y: n
  };
}
const ut = function(e, t, n) {
  const o = A(e.nodes, t), s = A(e.nodes, n), i = o.offsetLeft + t.offsetWidth / 2, l = o.offsetTop + t.offsetHeight / 2, c = s.offsetLeft + n.offsetWidth / 2, r = s.offsetTop + n.offsetHeight / 2, a = c - i, d = r - l, h = Math.sqrt(a * a + d * d), u = Math.max(50, Math.min(200, h * 0.3)), p = Math.abs(a), v = Math.abs(d);
  let m, y;
  if (h < 150) {
    const x = t.closest("me-main").className === "lhs" ? -1 : 1;
    m = { x: 200 * x, y: 0 }, y = { x: 200 * x, y: 0 };
  } else if (p > v * 1.5) {
    const x = a > 0 ? t.offsetWidth / 2 : -t.offsetWidth / 2, E = a > 0 ? -n.offsetWidth / 2 : n.offsetWidth / 2;
    m = { x: x + (a > 0 ? u : -u), y: 0 }, y = { x: E + (a > 0 ? -u : u), y: 0 };
  } else if (v > p * 1.5) {
    const x = d > 0 ? t.offsetHeight / 2 : -t.offsetHeight / 2, E = d > 0 ? -n.offsetHeight / 2 : n.offsetHeight / 2;
    m = { x: 0, y: x + (d > 0 ? u : -u) }, y = { x: 0, y: E + (d > 0 ? -u : u) };
  } else {
    const x = Math.atan2(d, a), E = t.offsetWidth / 2 * Math.cos(x), N = t.offsetHeight / 2 * Math.sin(x), f = -(n.offsetWidth / 2) * Math.cos(x), b = -(n.offsetHeight / 2) * Math.sin(x), w = u * 0.7 * (a > 0 ? 1 : -1), S = u * 0.7 * (d > 0 ? 1 : -1);
    m = { x: E + w, y: N + S }, y = { x: f - w, y: b - S };
  }
  return {
    delta1: { x: Math.round(m.x), y: Math.round(m.y) },
    delta2: { x: Math.round(y.x), y: Math.round(y.y) }
  };
}, Ne = function(e, t, n, o, s) {
  if (!t || !n)
    return;
  if (!o.delta1 || !o.delta2) {
    const C = ut(e, t, n);
    o.delta1 = C.delta1, o.delta2 = C.delta2;
  }
  const i = V(e, t, o.delta1), l = V(e, n, o.delta2), { x: c, y: r } = j(i), { ctrlX: a, ctrlY: d } = i, { ctrlX: h, ctrlY: u } = l, { x: p, y: v } = j(l), m = se(h, u, p, v);
  if (!m) return;
  const y = `M ${m.x1} ${m.y1} L ${p} ${v} L ${m.x2} ${m.y2}`;
  let g = "";
  if (o.bidirectional) {
    const C = se(a, d, c, r);
    if (!C) return;
    g = `M ${C.x1} ${C.y1} L ${c} ${r} L ${C.x2} ${C.y2}`;
  }
  const x = In(`M ${c} ${r} C ${a} ${d} ${h} ${u} ${p} ${v}`, y, g, o.style), { x: E, y: N } = ft(c, r, a, d, h, u, p, v), f = o.style?.labelColor || "rgb(235, 95, 82)", b = "a-" + o.id;
  x.id = b;
  const w = e.markdown ? e.markdown(o.label, o) : o.label, S = he(w, E, N, {
    anchor: "middle",
    color: f,
    dataType: "arrow",
    svgId: b
  });
  x.labelEl = S, x.arrowObj = o, x.dataset.linkid = o.id, e.labelContainer.appendChild(S), e.arrowSvg.appendChild(x), le(S), s || (e.arrows.push(o), e.currentArrow = x, gt(e, o, i, l));
}, uo = function(e, t, n = {}) {
  const o = {
    id: W(),
    label: "Custom Link",
    from: e.nodeObj.id,
    to: t.nodeObj.id,
    ...n
  };
  Ne(this, e, t, o), this.bus.fire("operation", {
    name: "createArrow",
    obj: o
  });
}, po = function(e) {
  ce(this);
  const t = { ...e, id: W() };
  Ne(this, this.findEle(t.from), this.findEle(t.to), t), this.bus.fire("operation", {
    name: "createArrow",
    obj: t
  });
}, go = function(e) {
  let t;
  if (e ? t = e : t = this.currentArrow, !t) return;
  ce(this);
  const n = t.arrowObj.id;
  this.arrows = this.arrows.filter((o) => o.id !== n), t.labelEl?.remove(), t.remove(), this.bus.fire("operation", {
    name: "removeArrow",
    obj: {
      id: n
    }
  });
}, mo = function(e) {
  this.currentArrow = e;
  const t = e.arrowObj, n = this.findEle(t.from), o = this.findEle(t.to), s = V(this, n, t.delta1), i = V(this, o, t.delta2);
  this.editable ? gt(this, t, s, i) : pt(e, ht), this.bus.fire("selectArrow", t);
}, yo = function() {
  ce(this), this.currentArrow = null, this.bus.fire("unselectArrow");
}, ae = function(e, t) {
  const n = document.createElementNS(M, "path");
  return k(n, {
    d: e,
    stroke: t,
    fill: "none",
    "stroke-width": "6",
    "stroke-linecap": "round",
    "stroke-linejoin": "round"
  }), n;
}, pt = function(e, t) {
  const n = document.createElementNS(M, "g");
  n.setAttribute("class", "arrow-highlight"), n.setAttribute("opacity", "0.45");
  const o = ae(e.line.getAttribute("d"), t);
  n.appendChild(o);
  const s = ae(e.arrow1.getAttribute("d"), t);
  if (n.appendChild(s), e.arrow2.getAttribute("d")) {
    const i = ae(e.arrow2.getAttribute("d"), t);
    n.appendChild(i);
  }
  e.insertBefore(n, e.firstChild);
}, bo = function(e) {
  const t = e.querySelector(".arrow-highlight");
  t && t.remove();
}, vo = function(e) {
  const t = e.querySelector(".arrow-highlight");
  if (!t) return;
  const n = t.querySelectorAll("path");
  n.length >= 1 && n[0].setAttribute("d", e.line.getAttribute("d")), n.length >= 2 && n[1].setAttribute("d", e.arrow1.getAttribute("d")), n.length >= 3 && e.arrow2.getAttribute("d") && n[2].setAttribute("d", e.arrow2.getAttribute("d"));
}, ce = function(e) {
  e.helper1?.destroy(), e.helper2?.destroy(), e.linkController.style.display = "none", e.P2.style.display = "none", e.P3.style.display = "none", e.currentArrow && bo(e.currentArrow);
}, gt = function(e, t, n, o) {
  const { linkController: s, P2: i, P3: l, line1: c, line2: r, nodes: a, map: d, currentArrow: h, bus: u } = e;
  if (!h) return;
  s.style.display = "initial", i.style.display = "initial", l.style.display = "initial", a.appendChild(s), a.appendChild(i), a.appendChild(l), pt(h, ht);
  let { x: p, y: v } = j(n), { ctrlX: m, ctrlY: y } = n, { ctrlX: g, ctrlY: x } = o, { x: E, y: N } = j(o);
  i.style.cssText = `top:${y}px;left:${m}px;`, l.style.cssText = `top:${x}px;left:${g}px;`, F(c, p, v, m, y), F(r, g, x, E, N), e.helper1 = Ve.create(i), e.helper2 = Ve.create(l), e.helper1.init(d, (f, b) => {
    m = m + f / e.scaleVal, y = y + b / e.scaleVal;
    const w = j({ ...n, ctrlX: m, ctrlY: y });
    p = w.x, v = w.y, i.style.top = y + "px", i.style.left = m + "px", ue(h, p, v, m, y, g, x, E, N, t), F(c, p, v, m, y), t.delta1.x = Math.round(m - n.cx), t.delta1.y = Math.round(y - n.cy), u.fire("updateArrowDelta", t);
  }), e.helper2.init(d, (f, b) => {
    g = g + f / e.scaleVal, x = x + b / e.scaleVal;
    const w = j({ ...o, ctrlX: g, ctrlY: x });
    E = w.x, N = w.y, l.style.top = x + "px", l.style.left = g + "px", ue(h, p, v, m, y, g, x, E, N, t), F(r, g, x, E, N), t.delta2.x = Math.round(g - o.cx), t.delta2.y = Math.round(x - o.cy), u.fire("updateArrowDelta", t);
  });
};
function xo() {
  this.arrowSvg.innerHTML = "", this.labelContainer.querySelectorAll('.svg-label[data-type="arrow"]').forEach((t) => t.remove());
  for (let t = 0; t < this.arrows.length; t++) {
    const n = this.arrows[t];
    try {
      Ne(this, this.findEle(n.from), this.findEle(n.to), n, !0);
    } catch {
    }
  }
  this.nodes.appendChild(this.arrowSvg);
}
function wo(e) {
  ce(this), e && e.labelEl && rt(this, e.labelEl, e.arrowObj);
}
function Eo() {
  this.arrows = this.arrows.filter((e) => oe(e.from, this.nodeData) && oe(e.to, this.nodeData));
}
const Co = function(e, t) {
  const n = ie(e);
  n.style && t.style && (t.style = Object.assign({}, n.style, t.style)), Object.assign(e, t);
  const o = this.arrowSvg.querySelector(`g[data-linkid="${e.id}"]`);
  if (o) {
    if (t.label !== void 0 && o.labelEl) {
      const l = this.markdown ? this.markdown(e.label, e) : e.label;
      o.labelEl.innerHTML = l;
    }
    const s = this.findEle(e.from), i = this.findEle(e.to);
    if (s && i) {
      if (!e.delta1 || !e.delta2) {
        const y = ut(this, s, i);
        e.delta1 = e.delta1 || y.delta1, e.delta2 = e.delta2 || y.delta2;
      }
      const l = V(this, s, e.delta1), c = V(this, i, e.delta2), { x: r, y: a } = j(l), { ctrlX: d, ctrlY: h } = l, { ctrlX: u, ctrlY: p } = c, { x: v, y: m } = j(c);
      ue(o, r, a, d, h, u, p, v, m, e), this.currentArrow?.arrowObj?.id === e.id && (this.P2.style.cssText = `top:${h}px;left:${d}px;`, this.P3.style.cssText = `top:${p}px;left:${u}px;`, F(this.line1, r, a, d, h), F(this.line2, u, p, v, m));
    }
  }
  this.bus.fire("operation", {
    name: "reshapeArrow",
    obj: e,
    origin: n
  });
}, So = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  createArrow: uo,
  createArrowFrom: po,
  editArrowLabel: wo,
  removeArrow: go,
  renderArrow: xo,
  reshapeArrow: Co,
  selectArrow: mo,
  tidyArrow: Eo,
  unselectArrow: yo
}, Symbol.toStringTag, { value: "Module" })), No = function(e) {
  if (e.length === 0) throw new Error("No selected node.");
  if (e.length === 1) {
    const r = e[0].nodeObj, a = e[0].nodeObj.parent;
    if (!a) throw new Error("Can not select root node.");
    const d = a.children.findIndex((h) => r === h);
    return {
      parent: a.id,
      start: d,
      end: d
    };
  }
  let t = 0;
  const n = e.map((r) => {
    let a = r.nodeObj;
    const d = [];
    for (; a.parent; ) {
      const h = a.parent, p = h.children?.indexOf(a);
      a = h, d.unshift({ node: a, index: p });
    }
    return d.length > t && (t = d.length), d;
  });
  let o = 0;
  e: for (; o < t; o++) {
    const r = n[0][o]?.node;
    for (let a = 1; a < n.length; a++)
      if (n[a][o]?.node !== r)
        break e;
  }
  if (!o) throw new Error("Can not select root node.");
  const s = n.map((r) => r[o - 1].index).sort(), i = s[0] || 0, l = s[s.length - 1] || 0, c = n[0][o - 1].node;
  if (!c.parent) throw new Error("Please select nodes in the same main topic.");
  return {
    parent: c.id,
    start: i,
    end: l
  };
}, To = function(e) {
  const t = document.createElementNS(M, "g");
  return t.setAttribute("id", e), t;
}, ze = function(e, t) {
  const n = document.createElementNS(M, "path");
  return k(n, {
    d: e,
    stroke: t || "#666",
    fill: "none",
    "stroke-linecap": "round",
    "stroke-width": "2"
  }), n;
}, ko = (e) => e.parentElement.parentElement, _o = function(e, { parent: t, start: n }) {
  const o = e.findEle(t), s = o.nodeObj;
  let i;
  return s.parent ? i = o.closest("me-main").className : i = e.findEle(s.children[n].id).closest("me-main").className, i;
}, Te = function(e, t) {
  const { id: n, label: o, parent: s, start: i, end: l, style: c } = t, { nodes: r, theme: a, summarySvg: d } = e, u = e.findEle(s).nodeObj, p = _o(e, t);
  let v = 1 / 0, m = 0, y = 0, g = 0;
  for (let G = i; G <= l; G++) {
    const ke = u.children?.[G];
    if (!ke)
      return e.removeSummary(n), null;
    const J = ko(e.findEle(ke.id)), { offsetLeft: Z, offsetTop: _e } = A(r, J), De = i === l ? 10 : 20;
    G === i && (y = _e + De), G === l && (g = _e + J.offsetHeight - De), Z < v && (v = Z), J.offsetWidth + Z > m && (m = J.offsetWidth + Z);
  }
  let x, E;
  const N = u.parent ? 10 : 0, f = y + N, b = g + N, w = (f + b) / 2, S = c?.stroke || a.cssVar["--color"], C = c?.labelColor || a.cssVar["--color"], T = "s-" + n, D = e.markdown ? e.markdown(o, t) : o;
  p === $.LHS ? (x = ze(`M ${v + 10} ${f} c -5 0 -10 5 -10 10 L ${v} ${b - 10} c 0 5 5 10 10 10 M ${v} ${w} h -10`, S), E = he(D, v - 20, w, { anchor: "end", color: C, dataType: "summary", svgId: T })) : (x = ze(`M ${m - 10} ${f} c 5 0 10 5 10 10 L ${m} ${b - 10} c 0 5 -5 10 -10 10 M ${m} ${w} h 10`, S), E = he(D, m + 20, w, { anchor: "start", color: C, dataType: "summary", svgId: T }));
  const L = To(T);
  return L.appendChild(x), e.labelContainer.appendChild(E), le(E), L.summaryObj = t, L.labelEl = E, d.appendChild(L), L;
}, Do = function(e = {}) {
  if (!this.currentNodes) return;
  const { currentNodes: t, summaries: n, bus: o } = this, { parent: s, start: i, end: l } = No(t), c = { id: W(), parent: s, start: i, end: l, label: "summary", style: e.style }, r = Te(this, c);
  n.push(c), this.editSummary(r), o.fire("operation", {
    name: "createSummary",
    obj: c
  });
}, Lo = function(e) {
  const t = W(), n = { ...e, id: t };
  Te(this, n), this.summaries.push(n), this.bus.fire("operation", {
    name: "createSummary",
    obj: n
  });
}, Ao = function(e) {
  const t = this.summaries.findIndex((n) => n.id === e);
  t > -1 && (this.summaries.splice(t, 1), this.nodes.querySelector("#s-" + e)?.remove(), this.nodes.querySelector("#label-s-" + e)?.remove()), this.bus.fire("operation", {
    name: "removeSummary",
    obj: { id: e }
  });
}, Mo = function(e) {
  const t = e.labelEl;
  t && t.classList.add("selected"), this.currentSummary = e, this.bus.fire("selectSummary", e.summaryObj);
}, Po = function() {
  this.currentSummary?.labelEl?.classList.remove("selected"), this.currentSummary = null, this.bus.fire("unselectSummary");
}, Oo = function() {
  this.summarySvg.innerHTML = "", this.summaries.forEach((e) => {
    try {
      Te(this, e);
    } catch {
    }
  }), this.nodes.insertAdjacentElement("beforeend", this.summarySvg);
}, $o = function(e) {
  e && e.labelEl && rt(this, e.labelEl, e.summaryObj);
}, Ho = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  createSummary: Do,
  createSummaryFrom: Lo,
  editSummary: $o,
  removeSummary: Ao,
  renderSummary: Oo,
  selectSummary: Mo,
  unselectSummary: Po
}, Symbol.toStringTag, { value: "Module" })), _ = "http://www.w3.org/2000/svg";
function jo(e, t) {
  const n = document.createElementNS(_, "svg");
  return k(n, {
    version: "1.1",
    xmlns: _,
    height: e,
    width: t
  }), n;
}
function Io(e, t) {
  return (parseInt(e) - parseInt(t)) / 2;
}
function Ro(e, t, n, o) {
  const s = document.createElementNS(_, "g");
  let i = "";
  return e.text ? i = e.text.textContent : i = e.childNodes[0].textContent, i.split(`
`).forEach((c, r) => {
    const a = document.createElementNS(_, "text");
    k(a, {
      x: n + parseInt(t.paddingLeft) + "",
      y: o + parseInt(t.paddingTop) + Io(t.lineHeight, t.fontSize) * (r + 1) + parseFloat(t.fontSize) * (r + 1) + "",
      "text-anchor": "start",
      "font-family": t.fontFamily,
      "font-size": `${t.fontSize}`,
      "font-weight": `${t.fontWeight}`,
      fill: `${t.color}`
    }), a.innerHTML = c, s.appendChild(a);
  }), s;
}
function Bo(e, t, n, o) {
  let s = "";
  e.nodeObj?.dangerouslySetInnerHTML ? s = e.nodeObj.dangerouslySetInnerHTML : e.text ? s = e.text.textContent : s = e.childNodes[0].textContent;
  const i = document.createElementNS(_, "foreignObject");
  k(i, {
    x: n + parseInt(t.paddingLeft) + "",
    y: o + parseInt(t.paddingTop) + "",
    width: t.width,
    height: t.height
  });
  const l = document.createElement("div");
  return k(l, {
    xmlns: "http://www.w3.org/1999/xhtml",
    style: `font-family: ${t.fontFamily}; font-size: ${t.fontSize}; font-weight: ${t.fontWeight}; color: ${t.color}; white-space: pre-wrap;`
  }), l.innerHTML = s, i.appendChild(l), i;
}
function Wo(e, t) {
  const n = getComputedStyle(t), { offsetLeft: o, offsetTop: s } = A(e.nodes, t), i = document.createElementNS(_, "rect");
  return k(i, {
    x: o + "",
    y: s + "",
    rx: n.borderRadius,
    ry: n.borderRadius,
    width: n.width,
    height: n.height,
    fill: n.backgroundColor,
    stroke: n.borderColor,
    "stroke-width": n.borderWidth
  }), i;
}
function ee(e, t, n = !1) {
  const o = getComputedStyle(t), { offsetLeft: s, offsetTop: i } = A(e.nodes, t), l = document.createElementNS(_, "rect");
  k(l, {
    x: s + "",
    y: i + "",
    rx: o.borderRadius,
    ry: o.borderRadius,
    width: o.width,
    height: o.height,
    fill: o.backgroundColor,
    stroke: o.borderColor,
    "stroke-width": o.borderWidth
  });
  const c = document.createElementNS(_, "g");
  c.appendChild(l);
  let r;
  return n ? r = Bo(t, o, s, i) : r = Ro(t, o, s, i), c.appendChild(r), c;
}
function Yo(e, t) {
  const n = getComputedStyle(t), { offsetLeft: o, offsetTop: s } = A(e.nodes, t), i = document.createElementNS(_, "a"), l = document.createElementNS(_, "text");
  return k(l, {
    x: o + "",
    y: s + parseInt(n.fontSize) + "",
    "text-anchor": "start",
    "font-family": n.fontFamily,
    "font-size": `${n.fontSize}`,
    "font-weight": `${n.fontWeight}`,
    fill: `${n.color}`
  }), l.innerHTML = t.textContent, i.appendChild(l), i.setAttribute("href", t.href), i;
}
function Xo(e, t) {
  const n = getComputedStyle(t), { offsetLeft: o, offsetTop: s } = A(e.nodes, t), i = document.createElementNS(_, "image");
  return k(i, {
    x: o + "",
    y: s + "",
    width: n.width + "",
    height: n.height + "",
    href: t.src
  }), i;
}
const te = 100, Fo = '<?xml version="1.0" standalone="no"?><!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">', Ko = (e, t = !1) => {
  const n = e.nodes, o = n.offsetHeight + te * 2, s = n.offsetWidth + te * 2, i = jo(o + "px", s + "px"), l = document.createElementNS(_, "svg"), c = document.createElementNS(_, "rect");
  k(c, {
    x: "0",
    y: "0",
    width: `${s}`,
    height: `${o}`,
    fill: e.theme.cssVar["--bgcolor"]
  }), i.appendChild(c), n.querySelectorAll(".subLines").forEach((h) => {
    const u = h.cloneNode(!0), { offsetLeft: p, offsetTop: v } = A(n, h.parentElement);
    u.setAttribute("x", `${p}`), u.setAttribute("y", `${v}`), l.appendChild(u);
  });
  const r = n.querySelector(".lines")?.cloneNode(!0);
  r && l.appendChild(r);
  const a = n.querySelector(".topiclinks")?.cloneNode(!0);
  a && l.appendChild(a);
  const d = n.querySelector(".summary")?.cloneNode(!0);
  return d && l.appendChild(d), n.querySelectorAll("me-tpc").forEach((h) => {
    h.nodeObj.dangerouslySetInnerHTML ? l.appendChild(ee(e, h, !t)) : (l.appendChild(Wo(e, h)), l.appendChild(ee(e, h.text, !t)));
  }), n.querySelectorAll(".tags > span").forEach((h) => {
    l.appendChild(ee(e, h));
  }), n.querySelectorAll(".icons > span").forEach((h) => {
    l.appendChild(ee(e, h));
  }), n.querySelectorAll(".hyper-link").forEach((h) => {
    l.appendChild(Yo(e, h));
  }), n.querySelectorAll("img").forEach((h) => {
    l.appendChild(Xo(e, h));
  }), k(l, {
    x: te + "",
    y: te + "",
    overflow: "visible"
  }), i.appendChild(l), i;
}, Vo = (e, t) => (t && e.insertAdjacentHTML("afterbegin", "<style>" + t + "</style>"), Fo + e.outerHTML);
function zo(e) {
  return new Promise((t, n) => {
    const o = new FileReader();
    o.onload = (s) => {
      t(s.target.result);
    }, o.onerror = (s) => {
      n(s);
    }, o.readAsDataURL(e);
  });
}
const Go = function(e = !1, t) {
  const n = Ko(this, e), o = Vo(n, t);
  return new Blob([o], { type: "image/svg+xml" });
}, qo = async function(e = !1, t) {
  const n = this.exportSvg(e, t), o = await zo(n);
  return new Promise((s, i) => {
    const l = new Image();
    l.setAttribute("crossOrigin", "anonymous"), l.onload = () => {
      const c = document.createElement("canvas");
      c.width = l.width, c.height = l.height, c.getContext("2d").drawImage(l, 0, 0), c.toBlob(s, "image/png", 1);
    }, l.src = o, l.onerror = i;
  });
}, Uo = /* @__PURE__ */ Object.freeze(/* @__PURE__ */ Object.defineProperty({
  __proto__: null,
  exportPng: qo,
  exportSvg: Go
}, Symbol.toStringTag, { value: "Module" }));
function Jo(e, t) {
  return async function(...n) {
    const o = this.before[t];
    o && !await o.apply(this, n) || e.apply(this, n);
  };
}
const Ge = Object.keys(ot), mt = {};
for (let e = 0; e < Ge.length; e++) {
  const t = Ge[e];
  mt[t] = Jo(ot[t], t);
}
const Zo = {
  getObjById: oe,
  generateNewObj: yt,
  layout: Tt,
  linkDiv: Rn,
  editTopic: Pt,
  createWrapper: Dt,
  createParent: Lt,
  createChildren: At,
  createTopic: Mt,
  findEle: Ze,
  changeTheme: co,
  changeCompact: ao,
  ...Nn,
  ...mt,
  ...So,
  ...Ho,
  ...Uo,
  init(e) {
    if (e = JSON.parse(JSON.stringify(e)), !e || !e.nodeData) return new Error("MindElixir: `data` is required");
    e.direction !== void 0 && (this.direction = e.direction), e.compact !== void 0 && (this.compact = e.compact), this.changeTheme(e.theme || this.theme, !1), e.meta && (this.meta = e.meta), this.nodeData = e.nodeData, B(this.nodeData), this.arrows = e.arrows || [], this.summaries = e.summaries || [], this.tidyArrow(), this.toolBar && eo(this), this.keypress && $n(this, this.keypress), lo(this), this.disposable.push(Nt()), this.contextMenu && this.disposable.push(Wn(this, this.contextMenu)), this.allowUndo && this.disposable.push(Xn(this)), this.layout(), this.linkDiv(), this.toCenter();
  },
  destroy() {
    this.disposable.forEach((e) => e()), this.el && (this.el.innerHTML = ""), this.el = void 0, this.nodeData = void 0, this.arrows = void 0, this.summaries = void 0, this.currentArrow = void 0, this.currentNodes = void 0, this.currentSummary = void 0, this.theme = void 0, this.direction = void 0, this.bus = void 0, this.container = void 0, this.map = void 0, this.lines = void 0, this.linkController = void 0, this.arrowSvg = void 0, this.P2 = void 0, this.P3 = void 0, this.line1 = void 0, this.line2 = void 0, this.nodes = void 0, this.selection?.destroy(), this.selection = void 0;
  },
  /**
   * @public
   * @param {boolean} enable
   */
  enableMobileMultiSelect(e) {
    this.mobileMultiSelect = e;
  }
}, Qo = "5.14.0";
function es(e) {
  return {
    x: 0,
    y: 0,
    moved: !1,
    // differentiate click and move
    mousedown: !1,
    handlePointerDown(t) {
      this.moved = !1;
      const n = t.target, o = e.mouseSelectionButton === 0 ? 2 : 0, s = e.spacePressed && t.button === 0 && t.pointerType === "mouse", i = !e.editable || t.button === o && t.pointerType === "mouse" || t.pointerType === "touch";
      !s && !i || (this.x = t.clientX, this.y = t.clientY, n.className !== "circle" && n.contentEditable !== "plaintext-only" && (this.mousedown = !0, n.setPointerCapture(t.pointerId)));
    },
    handlePointerMove(t) {
      if (!this.mousedown || t.target.contentEditable === "plaintext-only" && !e.spacePressed) return !1;
      const n = t.clientX - this.x, o = t.clientY - this.y;
      return this.x = t.clientX, this.y = t.clientY, this.moved = !0, e.move(n, o), !0;
    },
    handlePointerUp(t) {
      if (!this.mousedown) return;
      const n = t.target;
      n.hasPointerCapture && n.hasPointerCapture(t.pointerId) && n.releasePointerCapture(t.pointerId), this.mousedown = !1;
    },
    clear() {
      this.mousedown = !1, this.moved = !1;
    }
  };
}
function P({
  el: e,
  direction: t,
  editable: n,
  contextMenu: o,
  toolBar: s,
  keypress: i,
  mouseSelectionButton: l,
  selectionContainer: c,
  before: r,
  newTopicName: a,
  allowUndo: d,
  generateMainBranch: h,
  generateSubBranch: u,
  overflowHidden: p,
  compact: v,
  theme: m,
  alignment: y,
  scaleSensitivity: g,
  scaleMax: x,
  scaleMin: E,
  handleWheel: N,
  markdown: f,
  imageProxy: b,
  pasteHandler: w,
  mobileMultiSelect: S
}) {
  let C = null;
  const T = Object.prototype.toString.call(e);
  if (T === "[object HTMLDivElement]" ? C = e : T === "[object String]" && (C = document.querySelector(e)), !C) throw new Error("MindElixir: el is not a valid element");
  C.style.position = "relative", C.innerHTML = "", this.el = C, this.disposable = [], this.before = r || {}, this.newTopicName = a || "New Node", this.contextMenu = o ?? !0, this.toolBar = s ?? !0, this.keypress = i ?? !0, this.mouseSelectionButton = l ?? 0, this.direction = t ?? 1, this.editable = n ?? !0, this.allowUndo = d ?? !0, this.scaleSensitivity = g ?? 0.1, this.scaleMax = x ?? 1.4, this.scaleMin = E ?? 0.2, this.generateMainBranch = h || at, this.generateSubBranch = u || dt, this.overflowHidden = p ?? !1, this.compact = v ?? !1, this.alignment = y ?? "root", this.handleWheel = N ?? !0, this.markdown = f || void 0, this.imageProxy = b || void 0, this.currentNodes = [], this.currentArrow = null, this.scaleVal = 1, this.tempDirection = null, this.mobileMultiSelect = S ?? !1, this.panHelper = es(this), this.bus = jn(), this.container = document.createElement("div"), this.selectionContainer = c || this.container, this.container.className = "map-container";
  const D = window.matchMedia("(prefers-color-scheme: dark)");
  this.theme = m || (D.matches ? ge : pe);
  const L = document.createElement("div");
  L.className = "map-canvas", this.map = L, this.container.setAttribute("tabindex", "0"), this.container.appendChild(this.map), this.el.appendChild(this.container), this.nodes = document.createElement("me-nodes"), this.lines = q("lines"), this.summarySvg = q("summary"), this.linkController = q("linkcontroller"), this.P2 = document.createElement("div"), this.P3 = document.createElement("div"), this.P2.className = this.P3.className = "circle", this.P2.style.display = this.P3.style.display = "none", this.line1 = Ie(), this.line2 = Ie(), this.linkController.appendChild(this.line1), this.linkController.appendChild(this.line2), this.arrowSvg = q("topiclinks"), this.labelContainer = document.createElement("div"), this.labelContainer.className = "label-container", this.map.appendChild(this.nodes), this.overflowHidden ? this.container.style.overflow = "hidden" : this.disposable.push(Hn(this)), w && (this.pasteHandler = w);
}
P.prototype = Zo;
Object.defineProperty(P.prototype, "currentNode", {
  get() {
    return this.currentNodes[this.currentNodes.length - 1];
  },
  enumerable: !0
});
P.LEFT = 0;
P.RIGHT = 1;
P.SIDE = 2;
P.THEME = pe;
P.DARK_THEME = ge;
P.version = Qo;
P.E = Ze;
P.new = (e) => ({
  nodeData: {
    id: W(),
    topic: e || "new topic",
    children: []
  }
});
export {
  ge as DARK_THEME,
  ts as LEFT,
  ns as RIGHT,
  os as SIDE,
  pe as THEME,
  P as default
};
