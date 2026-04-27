const express = require("express");
const axios = require("axios");
const cors = require("cors");
const FormData = require("form-data");

const app = express();
app.use(cors());
app.use(express.json({ limit: "10mb" }));

const { GoogleGenerativeAI } = require("@google/generative-ai");

// 🔥 YOUR API KEY (keep it safe later)
const genAI = new GoogleGenerativeAI("AIzaSyDrXwZIokJkH8a7PLafFYb15xm5OXKvVsU");

// 🔗 HF Vision API
const HF_URL = "https://sanjaypadmaraj-ai-vision-detection.hf.space/describe";

// 📊 FULL SENSOR DATA
let latestData = {
    distance1: 0,
    distance2: 0,
    water: 0,
    ldr: 0,
    sos: 0,
    lat: 0,
    lon: 0
};

// =============================
// 🧠 SENSOR INTELLIGENCE
// =============================
function analyzeEnvironment(data) {
    const { distance1, distance2, water, sos } = data;

    let alerts = [];

    if (distance1 < 50) alerts.push("Obstacle ahead");
    if (distance2 < 30) alerts.push("Obstacle on the side");

    if (water === 1) alerts.push("Water detected");

    if (distance1 < 50 && water === 1) {
        alerts.push("Danger: obstacle and water");
    }

    if (sos === 1) alerts.push("Emergency! User needs help");

    return alerts;
}

// =============================
// 🌍 REVERSE GEOCODING
// =============================
async function getAddress(lat, lon) {
    try {
        const res = await axios.get(
            `https://nominatim.openstreetmap.org/reverse`,
            {
                params: {
                    format: "json",
                    lat,
                    lon
                },
                headers: {
                    "User-Agent": "leo-assist-app"
                }
            }
        );

        return res.data.display_name || "Unknown location";
    } catch (err) {
        console.log("🌍 Geocode error:", err.message);
        return null;
    }
}

// =============================
// 📡 ESP32 → SERVER
// =============================
app.post("/data", (req, res) => {
    latestData = {
        ...latestData,
        ...req.body
    };

    console.log("📡 ESP32:", latestData);
    res.send("OK");
});

// =============================
// 🔄 LIVE DATA FOR FRONTEND
// =============================
app.get("/live", async (req, res) => {
    const alerts = analyzeEnvironment(latestData);

    let mapLink = null;
    let address = null;

    if (latestData.lat && latestData.lon) {
        mapLink = `https://www.google.com/maps?q=${latestData.lat},${latestData.lon}`;
        address = await getAddress(latestData.lat, latestData.lon);
    }

    res.json({
        ...latestData,
        alerts,
        mapLink,
        address
    });
});

// =============================
// 📷 GOOGLE VISION (FAST + RELIABLE)
// =============================
app.post("/vision", async (req, res) => {
    try {
        const base64Image = req.body.image;

        if (!base64Image) {
            return res.status(400).json({ error: "No image" });
        }

        // Extract base64
        const base64Data = base64Image.split(",")[1];

        // 🔑 YOUR GOOGLE API KEY
        const API_KEY = "AIzaSyASdL8nw28ABCXCXAxdFt-GU1H3CHpcxqs";

        const response = await axios.post(
            `https://vision.googleapis.com/v1/images:annotate?key=${API_KEY}`,
            {
                requests: [
                    {
                        image: {
                            content: base64Data
                        },
                        features: [
                            { type: "LABEL_DETECTION", maxResults: 5 }
                        ]
                    }
                ]
            }
        );

        const labels = response.data.responses[0].labelAnnotations || [];

        let description = "I don't see any obstacles around you";

        // Convert labels to lowercase
        const detected = labels.map(l => l.description.toLowerCase());

        // =============================
        // 🎯 PRIORITY-BASED DETECTION
        // =============================

        // 🚨 1. HUMAN (TOP PRIORITY)
        if (detected.some(l =>
            ["person", "human", "man", "woman", "face", "head"].includes(l)
        )) {
            if (latestData.distance1 < 50) {
                description = "A person is very close in front of you";
            } else {
                description = "There is a person ahead";
            }
        }

        // 🚗 2. VEHICLES
        else if (detected.some(l =>
            ["car", "vehicle", "bus", "truck", "motorcycle", "bicycle"].includes(l)
        )) {
            description = "There is a vehicle nearby";
        }

        // 🧱 3. OBSTACLES
        else if (detected.some(l =>
            ["wall", "pole", "fence", "barrier", "pillar", "door"].includes(l)
        )) {
            if (latestData.distance1 < 50) {
                description = "Obstacle very close ahead";
            } else {
                description = "There is an obstacle ahead";
            }
        }

        // 🪜 4. STAIRS
        else if (detected.some(l =>
            ["stairs", "steps", "staircase"].includes(l)
        )) {
            description = "There are stairs ahead";
        }

        // 💧 5. WATER
        else if (detected.some(l =>
            ["water", "puddle", "river", "wet"].includes(l)
        )) {
            description = "Water detected ahead";
        }

        // 🚧 6. ROAD / TRAFFIC AREA
        else if (detected.some(l =>
            ["road", "street", "highway", "lane"].includes(l)
        )) {
            description = "You are facing a road";
        }

        // 🪑 7. OBJECTS (GENERAL)
        else if (detected.some(l =>
            ["chair", "table", "bench", "sofa"].includes(l)
        )) {
            description = "There is an object in front of you";
        }

        // 🌳 8. OUTDOOR / NATURE
        else if (detected.some(l =>
            ["tree", "plant", "grass"].includes(l)
        )) {
            description = "There is a plant or tree nearby";
        }

        // 🏠 9. INDOOR ENVIRONMENT
        else if (detected.some(l =>
            ["room", "indoor", "furniture"].includes(l)
        )) {
            description = "You are indoors";
        }

        res.json({ description });

    } catch (err) {
        console.error("🔥 Vision Error:", err.response?.data || err.message);

        res.status(500).json({
            error: "Vision failed",
            details: err.response?.data || err.message
        });
    }
});

// =============================
// 🤖 AI TEXT (FULLY FIXED)
// =============================
app.post("/ai", async (req, res) => {
    console.log("🧠 AI HIT:", req.body);

    try {
        const { input, context } = req.body;

        // fallback safety
        const data = context || latestData;

        const model = genAI.getGenerativeModel({
            model: "gemini-2.5-flash-lite"
        });

        const prompt = `
You are a smart assistant for a blind person.

Sensor data:
${JSON.stringify(data)}

Rules:
- Keep answers short and clear
- Warn about danger (obstacles, water)
- Help with navigation
- Speak naturally

User: ${input}
`;

        const result = await model.generateContent(prompt);

        const text = result.response.text();

        res.json({ result: text });

    } catch (err) {
        console.error("❌ GEMINI ERROR:", err.message);

        res.json({
            result: "AI is not responding. Check API key or internet."
        });
    }
});

// =============================
app.listen(5000, "0.0.0.0", () => {
    console.log("🚀 Server running on port 5000");
});