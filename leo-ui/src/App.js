import { useEffect, useState, useRef } from "react";

function App() {
  const SERVER = "http://10.234.19.169:5000";

  const [tab, setTab] = useState("user");

  const [data, setData] = useState({
    distance1: 0,
    distance2: 0,
    water: 0,
    ldr: 0,
    sos: 0,
    fall: 0,
    alerts: [],
    lat: 0,
    lon: 0,
    mapLink: "",
    address: "",
    temp: 28.5,
    battery: 87,
    tilt: 2,
    aiQuality: "Good"
  });

  const [aiText, setAiText] = useState("System Ready...");
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);

  const videoRef = useRef(null);
  const speakingRef = useRef(false);
  const lastLocationRef = useRef("");

  // ✅ NEW STATE TRACKING
  const lastStateRef = useRef({
    obstacle: false,
    water: 0,
    isDark: null,
    sos: 0
  });

  const lastSpokenRef = useRef({
    distance: 0,
    water: 0,
    ldr: 0,
    gps: 0,
    sos: 0
  });

  // 🔊 SPEAK
  const speak = (text) => {
    speechSynthesis.cancel();

    const msg = new SpeechSynthesisUtterance(text);
    msg.rate = 1;
    msg.pitch = 1.1;

    speechSynthesis.speak(msg);
  };
  // 👋 WELCOME MESSAGE (ADD HERE)
  useEffect(() => {
    const hasSpoken = sessionStorage.getItem("welcomed");

    if (!hasSpoken) {
      setTimeout(() => {
        speak("Welcome to Vision X. System is now active.");
        sessionStorage.setItem("welcomed", "true");
      }, 1000);
    }
  }, []);

  // 📡 LIVE DATA
  useEffect(() => {
    const interval = setInterval(() => {
      fetch(`${SERVER}/live`)
        .then(res => res.json())
        .then(d => {
          setData(prev => ({
            ...prev,
            ...d,

            // 🌡 Temperature
            temp: (d.temp && d.temp > 0 && d.temp < 100)
              ? d.temp
              : prev.temp,

            // 🔋 Battery
            battery: (d.battery !== undefined && d.battery >= 0 && d.battery <= 100)
              ? d.battery
              : prev.battery,

            // 🧭 Tilt
            tilt: (d.tilt !== undefined && d.tilt !== null)
              ? d.tilt
              : prev.tilt,

            // 🤖 AI Quality
            aiQuality: d.aiQuality || prev.aiQuality
          }));

          const now = Date.now();

          // =============================
          // 🚧 DISTANCE ALERT
          // =============================
          const obstacle = d.distance1 < 50 || d.distance2 < 30;

          if (obstacle && !lastStateRef.current.obstacle) {
            if (now - lastSpokenRef.current.distance > 5000) {
              speak("Obstacle nearby");
              lastSpokenRef.current.distance = now;
            }
          }
          lastStateRef.current.obstacle = obstacle;

          // =============================
          // 💧 WATER ALERT
          // =============================
          if (d.water === 1 && lastStateRef.current.water === 0) {
            if (now - lastSpokenRef.current.water > 10000) {
              speak("Water detected");
              lastSpokenRef.current.water = now;
            }
          }
          lastStateRef.current.water = d.water;

          // =============================
          // 🌙 LDR CHANGE ALERT
          // =============================
          const isDark = d.ldr < 1000;

          if (
            lastStateRef.current.isDark !== null &&
            isDark !== lastStateRef.current.isDark
          ) {
            if (now - lastSpokenRef.current.ldr > 10000) {
              speak(isDark ? "It is dark now" : "It is bright now");
              lastSpokenRef.current.ldr = now;
            }
          }
          lastStateRef.current.isDark = isDark;

          // =============================
          // 🧭 GPS CHANGE ALERT (FINAL FIX)
          // =============================
          if (d.lat !== 0 && d.lon !== 0) {
            const lat = parseFloat(d.lat).toFixed(3);
            const lon = parseFloat(d.lon).toFixed(3);

            const locKey = `${lat},${lon}`;

            if (lastLocationRef.current !== locKey) {
              lastLocationRef.current = locKey;

              // slight delay to avoid clash with other alerts
              setTimeout(() => {
                if (d.address && d.address.length > 5) {
                  speak(`You are near ${d.address}`, true);
                } else {
                  speak("Location updated");
                }
              }, 500);
            }
          }
          // =============================
          // 🚨 SOS ALERT
          // =============================
          if (d.sos === 1 && lastStateRef.current.sos === 0) {
            if (now - lastSpokenRef.current.sos > 20000) {
              speak("Emergency activated");
              lastSpokenRef.current.sos = now;
            }
          }
          lastStateRef.current.sos = d.sos;

        })
        .catch(err => {
          console.error("Live fetch error:", err);
        });
    }, 1200);

    return () => clearInterval(interval);
  }, []);

  // 🎤 VOICE
  const startVoice = () => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert("❌ Speech recognition not supported in this browser");
      return;
    }

    const rec = new SpeechRecognition();

    rec.lang = "en-IN";
    rec.continuous = false;
    rec.interimResults = false;

    setListening(true);
    setAiText("🎙 Listening..."); // 👈 FORCE UI UPDATE

    rec.onstart = () => {
      console.log("🎤 Mic started");
    };

    rec.onresult = async (e) => {
      console.log("✅ Speech detected");

      const text = e.results[0][0].transcript;

      setListening(false);

      // ✅ SHOW TRANSCRIPTION
      setAiText(`You: ${text}`);

      try {
        const res = await fetch(`${SERVER}/ai`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            input: text,
            context: data
          })
        });

        const d = await res.json();

        // ✅ SHOW AI RESPONSE
        setAiText(`AI: ${d.result}`);

        speak(d.result);

      } catch (err) {
        console.error("❌ FETCH ERROR:", err);
        setAiText("❌ Voice assistant failed (backend issue)");
      }
    };

    rec.onerror = (e) => {
      console.error("❌ Speech error:", e);
      setListening(false);
      setAiText("❌ Mic error / permission denied");
    };

    rec.onend = () => {
      console.log("🎤 Mic ended");
      setListening(false);
    };

    rec.start();
  };

  // 📷 CAMERA
  const startCamera = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    videoRef.current.srcObject = stream;
  };

  // 🧠 VISION
  const captureAndSend = async () => {
    try {
      setLoading(true);
      setAiText("🧠 Analyzing scene...");

      const canvas = document.createElement("canvas");
      const video = videoRef.current;

      canvas.width = 320;
      canvas.height = 240;

      const ctx = canvas.getContext("2d");
      ctx.drawImage(video, 0, 0);

      const img = canvas.toDataURL("image/jpeg", 0.6);

      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 15000);

      const res = await fetch(`${SERVER}/vision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: img }),
        signal: controller.signal
      });

      clearTimeout(timeout);

      const d = await res.json();
      const output = d.description || "No result";

      setAiText(output);
      speak(output);

    } catch (err) {
      console.error("🔥 Vision Error:", err);

      if (err.name === "AbortError") {
        setAiText("⚠️ Vision took too long. Try again.");
      } else {
        setAiText("❌ Vision failed. Check server.");
      }
    } finally {
      setLoading(false);
    }
  };

  // 🗺️ OPEN MAP
  const openMap = () => {
    if (data.mapLink) {
      window.open(data.mapLink, "_blank");
    } else {
      speak("Location not available");
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h1 style={styles.logo}>Vision X</h1>

        <div style={styles.controls}>
          <button style={styles.btn} onClick={() => setTab("user")}>User</button>
          <button style={styles.btn} onClick={() => setTab("care")}>Care</button>

          <button style={styles.voiceBtn} onClick={startVoice}>
            {listening ? "🎙 Listening..." : "🎤 Talk"}
          </button>
        </div>
      </div>

      {data.sos === 1 && (
        <div style={styles.sos}>🚨 EMERGENCY SOS ACTIVATED</div>
      )}

      {tab === "care" && (
        <div style={styles.grid}>
          <Card title="Front Sensor" value={`${data.distance1} cm`} danger={data.distance1 < 50} />
          <Card title="Side Sensor" value={`${data.distance2} cm`} danger={data.distance2 < 30} />
          <Card title="Water" value={data.water ? "Detected" : "Safe"} danger={data.water} />
          <Card title="Light" value={data.ldr > 1000 ? "Dark" : "Bright"} />
          <Card title="Temperature" value={data.temp ? `${data.temp} °C` : "N/A"} />
          <Card title="Fall Detection" value={data.fall ? "FALL DETECTED" : "Normal"} danger={data.fall} />
          <Card title="Battery" value={`${data.battery.toFixed(2)} %`} danger={data.battery < 25} />
          <Card title="Tilt" value={`${data.tilt}`} />
          <Card title="AI Quality" value={data.aiQuality} />

          <div style={styles.card}>
            <h3>📍 Location</h3>
            <p>Lat: {data.lat}</p>
            <p>Lon: {data.lon}</p>

            {data.address && (
              <p style={{ fontSize: "12px", marginTop: "5px" }}>
                {data.address}
              </p>
            )}

            <button style={styles.btn} onClick={openMap}>
              Open Map
            </button>
          </div>

          <div style={styles.aiCard}>
            <h3>🧠 AI Assistant</h3>
            <div style={styles.aiText}>{aiText}</div>
          </div>
        </div>
      )}

      {/* 🔁 ONLY THIS PART CHANGED (USER MODE UI)*/}

      {tab === "user" && (
        <div style={styles.cameraCard}>

          <h3 style={{ marginBottom: "15px" }}>📷 Vision Control</h3>

          {/* 🎥 CAMERA PREVIEW */}
          <div style={styles.cameraPreview}>
            <video ref={videoRef} autoPlay style={styles.video}></video>

            {!videoRef.current?.srcObject && (
              <div style={styles.cameraOverlay}>
                Camera is off
              </div>
            )}
          </div>

          {/* 🎮 CONTROLS */}
          <div style={styles.userModeContainer}>

            <div style={styles.bigCircle} onClick={startVoice}>
              <span style={styles.bigIcon}>🎤</span>
              <p>Talk</p>
            </div>

            <div style={styles.bigCircle} onClick={startCamera}>
              <span style={styles.bigIcon}>📷</span>
              <p>Start</p>
            </div>

            <div style={styles.bigCircle} onClick={captureAndSend}>
              <span style={styles.bigIcon}>🔍</span>
              <p>Scan</p>
            </div>

          </div>

        </div>
      )}

      <div style={styles.aiCard}>
        <h3>🧠 AI Assistant</h3>
        <div style={styles.aiText}>{aiText}</div>
      </div>
    </div>
  );
}

// 🔹 CARD
const Card = ({ title, value, danger }) => (
  <div style={{
    ...styles.card,
    border: danger ? "1px solid #ff3b3b" : "1px solid rgba(0,255,255,0.4)",
    boxShadow: danger
      ? "0 0 15px rgba(255,0,0,0.7)"
      : "0 0 10px rgba(0,255,255,0.3)"
  }}>
    <h3>{title}</h3>
    <p style={{
      color: danger ? "#ff4d4d" : "#00ffff",
      fontSize: "20px"
    }}>
      {value}
    </p>
  </div>
);

// 🎨 STYLES (unchanged)
const styles = {
  container: {
    minHeight: "100vh",
    background: "linear-gradient(135deg,#050510,#0a0f2c)",
    color: "white",
    padding: "20px",
    fontFamily: "sans-serif"
  },
  cameraOverlay: {
    position: "absolute",
    top: 0,
    left: 0,
    width: "100%",
    height: "100%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "white",
    background: "rgba(0,0,0,0.5)",
    fontSize: "18px"
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "20px"
  },
  logo: { color: "#00ffff", textShadow: "0 0 10px cyan" },
  controls: { display: "flex", gap: "10px" },
  btn: {
    padding: "8px 14px",
    borderRadius: "10px",
    border: "none",
    background: "rgba(255,255,255,0.1)",
    color: "white",
    backdropFilter: "blur(10px)",
    cursor: "pointer"
  },
  voiceBtn: {
    padding: "10px 16px",
    borderRadius: "12px",
    background: "linear-gradient(45deg,#00ffff,#0066ff)",
    border: "none",
    color: "black",
    fontWeight: "bold",
    cursor: "pointer",
    boxShadow: "0 0 15px cyan"
  },
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit,minmax(250px,1fr))",
    gap: "20px"
  },
  card: {
    padding: "20px",
    borderRadius: "18px",
    background: "rgba(255,255,255,0.05)",
    backdropFilter: "blur(15px)"
  },
  aiCard: {
    padding: "20px",
    borderRadius: "18px",
    background: "rgba(0,0,0,0.4)",
    border: "1px solid cyan",
    boxShadow: "0 0 15px rgba(0,255,255,0.3)"
  },
  aiText: { marginTop: "10px", lineHeight: "1.5" },
  sos: {
    background: "red",
    padding: "12px",
    textAlign: "center",
    fontWeight: "bold"
  },
  userModeContainer: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    gap: "20px",
    flexWrap: "wrap"
  },

  bigCircle: {
    width: "100px",
    height: "100px",
    borderRadius: "50%",
    background: "rgba(255,255,255,0.08)",
    backdropFilter: "blur(15px)",
    display: "flex",
    flexDirection: "column",
    justifyContent: "center",
    alignItems: "center",
    cursor: "pointer",
    border: "2px solid rgba(0,255,255,0.6)",
    boxShadow: "0 0 20px rgba(0,255,255,0.6)",
    transition: "0.2s"
  },

  bigIcon: {
    fontSize: "30px",
    marginBottom: "5px"
  },

  cameraCard: {
    gridColumn: "span 2",
    padding: "20px",
    borderRadius: "20px",
    background: "rgba(0,0,0,0.5)",
    border: "1px solid rgba(0,255,255,0.4)",
    boxShadow: "0 0 20px rgba(0,255,255,0.2)"
  },

  cameraPreview: {
    position: "relative",
    width: "100%",
    height: "400px",
    borderRadius: "15px",
    overflow: "hidden",
    marginBottom: "15px",
    border: "1px solid rgba(255,255,255,0.2)"
  },

  video: {
    width: "100%",
    height: "100%",
    objectFit: "contain",
    borderRadius: "12px"
  },
};

export default App;