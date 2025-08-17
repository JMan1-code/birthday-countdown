import streamlit as st
import datetime
import base64
import json
import io
from PIL import Image
from datetime import timedelta
from streamlit_autorefresh import st_autorefresh

# ---------- Helper Functions ----------
def get_countdown(target):
    now = datetime.datetime.now()
    delta = target - now
    total_seconds = max(delta.total_seconds(), 0)

    days = delta.days if delta.days > 0 else 0
    hours, remainder = divmod(delta.seconds if delta.seconds > 0 else 0, 3600)
    minutes, seconds = divmod(remainder, 60)

    return days, hours, minutes, seconds, total_seconds

def load_and_resize_image(uploaded_file, size=(50, 50)):
    image = Image.open(uploaded_file)
    image = image.convert("RGBA")
    image.thumbnail(size)
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str

# ---------- Session State Setup ----------
if "countdowns" not in st.session_state:
    st.session_state.countdowns = []

if "selected" not in st.session_state:
    st.session_state.selected = 0

# Auto-refresh every second
st_autorefresh(interval=1000, key="refresh")

# ---------- UI ----------
st.title("🎉 Birthday Countdown App")

with st.expander("Add a new countdown"):
    name = st.text_input("Name")
    date = st.date_input(
        "Date of Birth",
        value=datetime.date(2000, 1, 1),
        min_value=datetime.date(1900, 1, 1),
        max_value=datetime.date.today()
    )
    photo = st.file_uploader("Upload icon photo (PNG/JPG)", type=["png", "jpg", "jpeg"])

    if photo is not None:
        st.image(photo, caption="Uploaded icon preview", width=100)

    if st.button("Add countdown"):
        if not name.strip():
            st.error("Please enter a name")
        elif photo is None:
            st.error("Please upload a photo")
        else:
            dob = datetime.datetime.combine(date, datetime.time(0, 0))
            now = datetime.datetime.now()

            this_year_birthday = dob.replace(year=now.year)
            if this_year_birthday < now:
                next_birthday = dob.replace(year=now.year + 1)
            else:
                next_birthday = this_year_birthday

            dt = next_birthday
            age = dt.year - dob.year
            st.markdown(f"**Turning {age} years old! 🎂**")
            img_b64 = load_and_resize_image(photo)
            st.session_state.countdowns.append({
                "name": name,
                "datetime": dt,
                "img_b64": img_b64,
                "color": f"hsl({len(st.session_state.countdowns)*70 % 360}, 80%, 60%)"
            })
            st.success(f"Added countdown for {name}")

if not st.session_state.countdowns:
    st.info("Add a countdown to get started!")
    st.stop()

# Selection
selected_name = st.selectbox(
    "Select countdown to view",
    options=[cd["name"] for cd in st.session_state.countdowns],
    index=st.session_state.selected
)
st.session_state.selected = [cd["name"] for cd in st.session_state.countdowns].index(selected_name)

# Countdown Calculation
selected_cd = st.session_state.countdowns[st.session_state.selected]
days, hours, minutes, seconds, total_seconds = get_countdown(selected_cd["datetime"])

st.markdown(f"""
    <div style="text-align:center; margin-top: 100px; margin-bottom: 50px; font-size: 3rem; font-weight: bold;">
        {selected_cd['name']}'s Birthday Countdown:<br>
        {days}d {hours}h {minutes}m {seconds}s
    </div>
""", unsafe_allow_html=True)

# Prepare data for JS animation
SECONDS_IN_YEAR = 365 * 24 * 3600

def calculate_progress(birthday_dt):
    now = datetime.datetime.now()
    start_dt = birthday_dt - timedelta(days=365)
    elapsed_seconds = (now - start_dt).total_seconds()
    return min(max(elapsed_seconds / SECONDS_IN_YEAR, 0), 1)

countdowns_js = []
for cd in st.session_state.countdowns:
    progress = calculate_progress(cd["datetime"])
    countdowns_js.append({
        "name": cd["name"],
        "progress": progress,
        "color": cd["color"],
        "img": f"data:image/png;base64,{cd['img_b64']}"
    })

json_data = json.dumps({
    "selectedIndex": st.session_state.selected,
    "countdowns": countdowns_js
})

# HTML + JS for animated canvas
html_code = f"""
<style>
  #progressCanvas {{
    width: 100%;
    background: #f9f9f9;
    display: block;
    margin: 0 auto;
  }}
</style>
<canvas id="progressCanvas" width="900"></canvas>
<script>
const data = {json_data};
const canvas = document.getElementById('progressCanvas');
const ctx = canvas.getContext('2d');

const iconRadius = 20;
const trailHeight = 40;
const width = canvas.width;
const height = trailHeight * (data.countdowns.length + 1);
canvas.height = height;

// Preload images
const loadedImages = [];
let imagesLoadedCount = 0;

function preloadImages(callback) {{
  data.countdowns.forEach((cd, index) => {{
    const img = new Image();
    img.src = cd.img;
    img.onload = () => {{
      loadedImages[index] = img;
      imagesLoadedCount++;
      if (imagesLoadedCount === data.countdowns.length) {{
        callback();
      }}
    }};
    img.onerror = () => {{
      imagesLoadedCount++;
      callback();
    }};
  }});
}}

function drawIcon(img, x, y) {{
  ctx.save();
  ctx.beginPath();
  ctx.arc(x, y, iconRadius, 0, Math.PI * 2);
  ctx.closePath();
  ctx.clip();
  ctx.drawImage(img, x - iconRadius, y - iconRadius, iconRadius * 2, iconRadius * 2);
  ctx.restore();
}}

function draw() {{
  ctx.clearRect(0, 0, width, height);

  let reordered = [data.countdowns[data.selectedIndex]];
  data.countdowns.forEach((cd, i) => {{
    if (i !== data.selectedIndex) reordered.push(cd);
  }});

  reordered.forEach((cd, index) => {{
    const y = trailHeight * (index + 1) - trailHeight / 2;
    ctx.fillStyle = cd.color;
    ctx.globalAlpha = 0.35;
    ctx.fillRect(0, y - trailHeight / 2, width * cd.progress, trailHeight);
    ctx.globalAlpha = 1;

    const originalIndex = data.countdowns.findIndex(c => c.name === cd.name);
    const img = loadedImages[originalIndex];
    const x = width * cd.progress;
    if (img) {{
      drawIcon(img, x, y);
    }}
  }});
}}

function animate() {{
  draw();
  requestAnimationFrame(animate);
}}

preloadImages(() => {{
  animate();
}});

// Celebration on full progress
function celebrate() {{
  const confettiCount = 150;
  for (let i = 0; i < confettiCount; i++) {{
    const confetti = document.createElement('div');
    confetti.style.position = 'fixed';
    confetti.style.width = '10px';
    confetti.style.height = '10px';
    confetti.style.backgroundColor = 'hsl(' + Math.random() * 360 + ', 100%, 70%)';
    confetti.style.left = Math.random() * window.innerWidth + 'px';
    confetti.style.top = '-10px';
    confetti.style.opacity = 0.8;
    confetti.style.borderRadius = '50%';
    confetti.style.animation = 'fall 3s linear forwards';
    confetti.style.zIndex = 9999;
    document.body.appendChild(confetti);
    setTimeout(() => confetti.remove(), 3000);
  }}
}}

const style = document.createElement('style');
style.innerHTML = `@keyframes fall {{
  0% {{ transform: translateY(0); opacity: 0.8; }}
  100% {{ transform: translateY(100vh); opacity: 0; }}
}}`;
document.head.appendChild(style);

function checkCelebrate() {{
  if (data.countdowns[data.selectedIndex].progress >= 1) {{
    celebrate();
  }}
}}
setInterval(checkCelebrate, 1000);
</script>
"""

# Set enough height for all bars + spacing
component_height = 100 + 60 * len(st.session_state.countdowns)
st.components.v1.html(html_code, height=component_height)
