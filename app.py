"""
SnapCanvas — Draw with your camera using OpenCV HSV color tracking.
"""

import cv2
import numpy as np
import streamlit as st
from PIL import Image
import io

st.set_page_config(
    page_title="SnapCanvas — Draw with Your Camera",
    page_icon="🎨",
    layout="wide"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background: #0B1120 !important;
    font-family: 'Outfit', sans-serif !important;
}

[data-testid="stAppViewBlockContainer"] {
    padding-top: 1.5rem !important;
}

[data-testid="stSidebar"] {
    background: #0D1526 !important;
    border-right: 1px solid rgba(0,180,216,0.3) !important;
}

[data-testid="stSidebar"] * {
    color: #E2E8F0 !important;
}

h1, h2, h3, p, label, div {
    color: #E2E8F0 !important;
}

.main-title {
    font-size: 5rem !important;
    font-weight: 800 !important;
    line-height: 1.05;
    background: linear-gradient(135deg, #00B4D8 0%, #10B981 60%, #8EE000 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
    color: transparent !important;
    margin-top: 0 !important;
    margin-bottom: 0.3rem !important;
    display: block;
    letter-spacing: -1px;
}

.subtitle {
    color: #94A3B8 !important;
    font-size: 0.95rem;
    margin-bottom: 1.5rem;
}

.how-it-works {
    background: rgba(0, 180, 216, 0.08);
    border: 1px solid rgba(0, 180, 216, 0.35);
    border-radius: 14px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1.2rem;
}

.how-it-works p {
    color: #CBD5E1 !important;
    font-size: 0.9rem;
    margin: 0.3rem 0;
}

.how-it-works strong {
    color: #00B4D8 !important;
}

.section-card {
    background: rgba(13, 21, 38, 0.85);
    border: 1px solid rgba(0,180,216,0.2);
    border-radius: 16px;
    padding: 1.3rem;
    margin-bottom: 1rem;
}

.badge {
    display: inline-block;
    padding: 5px 14px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
    margin-right: 8px;
    margin-bottom: 10px;
}

.badge-teal { background: rgba(0,180,216,0.15); border: 1px solid #00B4D8; color: #00B4D8 !important; }
.badge-green { background: rgba(16,185,129,0.15); border: 1px solid #10B981; color: #10B981 !important; }

div.stButton > button {
    background: linear-gradient(135deg, rgba(0,180,216,0.2), rgba(16,185,129,0.2)) !important;
    border: 1px solid #00B4D8 !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    border-radius: 10px !important;
    width: 100% !important;
}
div.stButton > button:hover {
    background: linear-gradient(135deg, #00B4D8, #10B981) !important;
    color: #0B1120 !important;
}

.stDeprecationWarning { display: none !important; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Session State ──────────────────────────────────────────────
if "canvas" not in st.session_state:
    st.session_state.canvas = np.zeros((480, 640, 3), dtype=np.uint8)
if "prev_point" not in st.session_state:
    st.session_state.prev_point = None
if "color_bgr" not in st.session_state:
    st.session_state.color_bgr = (0, 180, 216)   # Teal in BGR
if "color_hex" not in st.session_state:
    st.session_state.color_hex = "#00B4D8"
if "brush_size" not in st.session_state:
    st.session_state.brush_size = 12
# Default HSV for ORANGE marker (pencil/pen)
if "h_range" not in st.session_state:
    st.session_state.h_range = (5, 20)
if "s_range" not in st.session_state:
    st.session_state.s_range = (150, 255)
if "v_range" not in st.session_state:
    st.session_state.v_range = (100, 255)
if "gallery" not in st.session_state:
    st.session_state.gallery = []

def hex_to_bgr(h):
    h = h.lstrip('#')
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return (b, g, r)

# ── SIDEBAR ────────────────────────────────────────────────────
st.sidebar.markdown("## 🎛️ Controls")

st.sidebar.markdown("### 🎨 Drawing Color")
c1, c2, c3, c4 = st.sidebar.columns(4)
with c1:
    if st.button("Teal", key="t"):
        st.session_state.color_hex = "#00B4D8"
        st.session_state.color_bgr = (216, 180, 0)
with c2:
    if st.button("Green", key="g"):
        st.session_state.color_hex = "#10B981"
        st.session_state.color_bgr = (129, 185, 16)
with c3:
    if st.button("Lime", key="l"):
        st.session_state.color_hex = "#8EE000"
        st.session_state.color_bgr = (0, 224, 142)
with c4:
    if st.button("Red", key="r"):
        st.session_state.color_hex = "#EF4444"
        st.session_state.color_bgr = (68, 68, 239)

picked = st.sidebar.color_picker("Custom color:", st.session_state.color_hex)
if picked != st.session_state.color_hex:
    st.session_state.color_hex = picked
    st.session_state.color_bgr = hex_to_bgr(picked)

st.sidebar.markdown("---")
st.session_state.brush_size = st.sidebar.slider("Brush Size:", 2, 40, st.session_state.brush_size)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎯 Marker Color Detection")
st.sidebar.caption("Match these sliders to your **physical marker/object** color:")

marker_presets = st.sidebar.selectbox("Quick Preset:", [
    "🟠 Orange (pencil/pen cap)",
    "🔵 Blue (blue marker/cap)",
    "🟢 Green (green object)",
    "🔴 Red (red marker)",
    "🟡 Yellow (yellow object)",
])

if st.sidebar.button("Apply Preset"):
    presets = {
        "🟠 Orange (pencil/pen cap)": ((5, 20), (150, 255), (100, 255)),
        "🔵 Blue (blue marker/cap)":  ((100, 130), (100, 255), (80, 255)),
        "🟢 Green (green object)":    ((40, 80), (80, 255), (80, 255)),
        "🔴 Red (red marker)":        ((0, 10), (120, 255), (80, 255)),
        "🟡 Yellow (yellow object)":  ((20, 40), (100, 255), (100, 255)),
    }
    h, s, v = presets[marker_presets]
    st.session_state.h_range = h
    st.session_state.s_range = s
    st.session_state.v_range = v

h_range = st.sidebar.slider("Hue (H):", 0, 179, st.session_state.h_range)
s_range = st.sidebar.slider("Saturation (S):", 0, 255, st.session_state.s_range)
v_range = st.sidebar.slider("Value/Brightness (V):", 0, 255, st.session_state.v_range)
st.session_state.h_range = h_range
st.session_state.s_range = s_range
st.session_state.v_range = v_range

st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Clear Canvas"):
    st.session_state.canvas = np.zeros((480, 640, 3), dtype=np.uint8)
    st.session_state.prev_point = None

# ── MAIN UI ───────────────────────────────────────────────────
st.markdown('''
<div style="
    font-family: Outfit, sans-serif;
    font-size: 5rem;
    font-weight: 800;
    line-height: 1.05;
    letter-spacing: -2px;
    background: linear-gradient(135deg, #00B4D8 0%, #10B981 55%, #8EE000 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-top: 0;
    margin-bottom: 0.3rem;
">🎨 SnapCanvas</div>
<div style="color:#94A3B8; font-size:1rem; margin-bottom:1rem; font-family:Outfit,sans-serif;">
    Draw with your camera — powered by OpenCV color tracking
</div>
''', unsafe_allow_html=True)

# Status badges
st.markdown(f"""
<span class="badge badge-teal">Drawing Color: <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:{st.session_state.color_hex};margin-left:4px;vertical-align:middle;"></span> {st.session_state.color_hex}</span>
<span class="badge badge-green">Brush: {st.session_state.brush_size}px</span>
""", unsafe_allow_html=True)

# How it works banner
st.markdown("""
<div class="how-it-works">
<p><strong>📖 How to use this app:</strong></p>
<p>1️⃣ <strong>Hold a colored object</strong> (e.g. orange pencil, blue pen cap, green tape) in front of your camera.</p>
<p>2️⃣ <strong>Take a photo</strong> — OpenCV detects the object using HSV color tracking and marks its position on the canvas.</p>
<p>3️⃣ <strong>Take multiple photos</strong> in different positions to build up a drawing — each photo extends the line on the canvas.</p>
<p>4️⃣ The <strong>right panel</strong> shows the detected mask and final composite drawing. Click "Save to Gallery" to download your artwork.</p>
<p>⚙️ <strong>Not detecting your marker?</strong> Use the sidebar presets or HSV sliders to match your object's color.</p>
</div>
""", unsafe_allow_html=True)

col_cam, col_result = st.columns([1, 1])

with col_cam:
    st.markdown("### 📷 Step 1 — Take a Photo")
    st.caption("Position your colored marker/object in frame, then click the camera button below:")
    camera_file = st.camera_input(" ", label_visibility="collapsed")

    if camera_file:
        # Decode
        bytes_data = camera_file.getvalue()
        frame = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]

        # Resize canvas to match frame if needed
        if st.session_state.canvas.shape[:2] != (h, w):
            st.session_state.canvas = cv2.resize(
                st.session_state.canvas, (w, h), interpolation=cv2.INTER_NEAREST
            )

        # ─ GeeksforGeeks HSV Marker Tracking Core ─
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hsv = cv2.GaussianBlur(hsv, (9, 9), 0)

        lower = np.array([h_range[0], s_range[0], v_range[0]], dtype=np.uint8)
        upper = np.array([h_range[1], s_range[1], v_range[1]], dtype=np.uint8)

        mask = cv2.inRange(hsv, lower, upper)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=4)

        contours, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        centroid = None
        annotated = frame.copy()

        if contours:
            largest = max(contours, key=cv2.contourArea)
            if cv2.contourArea(largest) > 200:
                M = cv2.moments(largest)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    centroid = (cx, cy)
                    (ex, ey), er = cv2.minEnclosingCircle(largest)
                    cv2.circle(annotated, (int(ex), int(ey)), int(er), (0, 255, 255), 3)
                    cv2.circle(annotated, centroid, 8, (0, 0, 255), -1)
                    cv2.putText(annotated, "DETECTED", (cx + 12, cy - 12),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        # Draw on canvas
        if centroid:
            color = st.session_state.color_bgr
            sz = st.session_state.brush_size
            if st.session_state.prev_point:
                cv2.line(st.session_state.canvas, st.session_state.prev_point, centroid, color, sz, cv2.LINE_AA)
            cv2.circle(st.session_state.canvas, centroid, sz // 2, color, -1)
            st.session_state.prev_point = centroid
        else:
            st.session_state.prev_point = None

        # ─ Composite: canvas on top of frame ─
        gray_c = cv2.cvtColor(st.session_state.canvas, cv2.COLOR_BGR2GRAY)
        _, canvas_mask = cv2.threshold(gray_c, 5, 255, cv2.THRESH_BINARY)
        inv_mask = cv2.bitwise_not(canvas_mask)
        frame_bg = cv2.bitwise_and(frame, frame, mask=inv_mask)
        composite = cv2.add(frame_bg, st.session_state.canvas)

        # Store for result panel
        st.session_state._annotated = annotated
        st.session_state._mask = mask
        st.session_state._composite = composite
        st.session_state._centroid = centroid

with col_result:
    st.markdown("### 🖼️ Step 2 — Results")

    if "_composite" in st.session_state:
        centroid = st.session_state._centroid
        annotated = st.session_state._annotated
        mask = st.session_state._mask
        composite = st.session_state._composite

        # Detection status
        if centroid:
            st.success(f"✅ Marker detected at position {centroid} — drawing added to canvas!")
        else:
            st.warning("⚠️ No marker detected in this photo. Adjust the HSV sliders in the sidebar to match your object's color, or try the **Apply Preset** button.")

        # Mask preview (what OpenCV sees)
        tab1, tab2, tab3 = st.tabs(["🎨 Final Drawing", "📷 Annotated Camera", "🔍 Detection Mask"])

        with tab1:
            composite_rgb = cv2.cvtColor(composite, cv2.COLOR_BGR2RGB)
            st.image(composite_rgb, caption="Canvas + Camera Composite", use_container_width=True)

            pil = Image.fromarray(composite_rgb)
            buf = io.BytesIO()
            pil.save(buf, format="PNG")
            if st.button("📸 Save to Gallery & Download"):
                st.session_state.gallery.append(buf.getvalue())
                st.success("Saved!")
            if st.session_state.gallery:
                st.download_button(
                    "💾 Download Latest PNG",
                    data=st.session_state.gallery[-1],
                    file_name="drawing.png",
                    mime="image/png"
                )

        with tab2:
            ann_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
            st.image(ann_rgb, caption="OpenCV sees the marker highlighted in yellow", use_container_width=True)

        with tab3:
            st.image(mask, caption="White = detected marker region (should show your object)", use_container_width=True)
            st.caption("If this is all black, your marker color is outside the HSV range. Use the sidebar presets!")

    else:
        st.info("📷 Take a photo on the left to see results here.")

        # Show current canvas if it has anything
        canvas_rgb = cv2.cvtColor(st.session_state.canvas, cv2.COLOR_BGR2RGB)
        if canvas_rgb.max() > 0:
            st.markdown("**Current Canvas:**")
            st.image(canvas_rgb, use_container_width=True)
            pil = Image.fromarray(canvas_rgb)
            buf = io.BytesIO()
            pil.save(buf, format="PNG")
            st.download_button("💾 Download Canvas", data=buf.getvalue(),
                               file_name="canvas.png", mime="image/png")
