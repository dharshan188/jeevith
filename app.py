from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# ----------------- API KEYS -----------------
USDA_API_KEY = "QL9h3HBbQJyQhCA2DNXQnERfFXeKMxTOOUXYj1cu"
WEATHER_API_KEY = "396de8bb5145446a9ee92656250311"

# ----------------- WEATHER DATA -----------------
def get_weather(city):
    url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={city}&aqi=no"
    r = requests.get(url)
    if r.status_code == 200:
        d = r.json()
        return {
            "condition": d["current"]["condition"]["text"],
            "temp": d["current"]["temp_c"],
            "humidity": d["current"]["humidity"],
        }
    return None

# ----------------- NUTRIENTS FETCH -----------------
def get_food_nutrients(food):
    url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key={USDA_API_KEY}&query={food}"
    r = requests.get(url)
    nutrients = {}
    if r.status_code == 200:
        data = r.json()
        if "foods" in data and len(data["foods"]) > 0:
            food_data = data["foods"][0]
            for n in food_data.get("foodNutrients", []):
                name = n.get("nutrientName")
                val = n.get("value")
                unit = n.get("unitName", "")
                if name and val:
                    nutrients[name] = f"{val} {unit}"
    return nutrients

# ----------------- DEFICIENCY CALC -----------------
def calculate_deficiency(total, gender, height, weight):
    req = {
        "Protein": 50,
        "Vitamin C": 90,
        "Iron": 18 if gender.lower() == "female" else 8,
        "Calcium": 1000,
        "Fiber": 30,
    }
    bmi = weight / ((height / 100) ** 2)
    if bmi < 18.5:
        for k in req:
            req[k] *= 1.1
    elif bmi > 25:
        for k in req:
            req[k] *= 0.9
    defic = {}
    for n, need in req.items():
        val_str = total.get(n, "0").split()[0]
        try:
            val = float(val_str)
        except:
            val = 0.0
        if val < need * 0.6:
            defic[n] = round(need - val, 2)
    return defic

# ----------------- RECOMMEND FOODS -----------------
def recommend_foods(defic, weather):
    base = {
        "Protein": [("Chicken", 27, "g"), ("Eggs", 13, "g"), ("Paneer", 18, "g")],
        "Iron": [("Spinach", 2.7, "mg"), ("Liver", 6.5, "mg"), ("Beans", 3.7, "mg")],
        "Calcium": [("Milk", 120, "mg"), ("Curd", 80, "mg"), ("Almonds", 75, "mg")],
        "Fiber": [("Oats", 10, "g"), ("Apple", 4.5, "g"), ("Carrots", 3, "g")],
        "Vitamin C": [("Orange", 53, "mg"), ("Guava", 200, "mg"), ("Kiwi", 90, "mg")],
    }
    temp_foods = ["Cucumber", "Yogurt"] if weather["temp"] > 30 else ["Soup", "Eggs"]
    rec = []
    for n in defic.keys():
        rec += base.get(n, [])
    for f in temp_foods:
        rec.append((f, "-", "-"))
    return rec[:10]

# ----------------- ROUTES -----------------
@app.route("/")
def home():
    return render_template("nutri.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json
    city = data["city"]
    items = data["items"]
    gender = data["gender"]
    height = float(data["height"])
    weight = float(data["weight"])

    weather = get_weather(city)
    if not weather:
        return jsonify({"error": "Weather data not found"})

    total = {}
    for it in items:
        name = it["name"]
        qty = float(it["qty"])
        nut = get_food_nutrients(name)
        for k, v in nut.items():
            try:
                val = float(v.split()[0]) * qty
                unit = v.split()[1]
                if k in total:
                    old = float(total[k].split()[0])
                    total[k] = f"{round(old + val, 2)} {unit}"
                else:
                    total[k] = f"{round(val, 2)} {unit}"
            except:
                continue

    defic = calculate_deficiency(total, gender, height, weight)
    rec = recommend_foods(defic, weather)
    return jsonify({
        "weather": weather,
        "total_nutrients": total,
        "deficient": defic,
        "recommendations": rec
    })

if __name__ == "__main__":
    app.run(debug=True)
