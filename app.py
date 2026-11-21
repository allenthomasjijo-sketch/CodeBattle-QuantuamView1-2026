import random
import os
try:
    import anthropic
except ImportError:
    anthropic = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from flask import Flask, request, redirect, jsonify, send_from_directory
app = Flask(__name__, static_folder=".", static_url_path="")
START_MONEY = 1000
WIN_MONEY = 2500
BROKE_MONEY = 100
ROUNDS = 8
FEE = 2
good_news = [
    "NAME's new product is a giant hit!",
    "Influencers can't stop talking about NAME!",
    "NAME wins Company of the Year!",
]
bad_news = [
    "Scandal at NAME! The boss is in big trouble.",
    "NAME recalls thousands of broken products.",
    "A fire shuts down NAME's main factory.",
]
RULES = """You are part of Market Mayhem, a stock market game for students aged 11-14.
All companies are made up and no real money is used.
Keep everything friendly and kid-safe. Never mention real companies, real people or real stock tips.
Only talk about this game and money basics. Use simple words."""
def new_game():
    companies = [
        {"name": "ByteBurger", "product": "Fast food", "price": 20, "jump": 0.01},
        {"name": "GreenLeaf Farms", "product": "Healthy snacks", "price": 15, "jump": 0.015},
        {"name": "Zoomy Motors", "product": "Electric scooters", "price": 40, "jump": 0.02},
        {"name": "PixelPlay", "product": "Video games", "price": 30, "jump": 0.03},
        {"name": "RocketRide", "product": "Space tourism", "price": 60, "jump": 0.05},
    ]
    for c in companies:
        c["start"] = c["price"]
        c["last"] = c["price"]
        c["change"] = 0
        c["owned"] = 0
        c["bankrupt"] = False
    rita = {"cash": START_MONEY, "owned": {}, "strategy": "", "picks": {}}
    rita["scores"] = {"follow the hype": 0, "buy the dip": 0, "play it safe": 0, "go risky": 0}
    return {
        "round": 1,
        "cash": START_MONEY,
        "companies": companies,
        "rita": rita,
        "history": [],
        "messages": ["Welcome to Market Mayhem! Buy some shares, then press End round."],
        "status": "playing",
        "rumor": None,
        "coach": "",
    }
def ask_claude(prompt):
    if anthropic is None or os.environ.get("ANTHROPIC_API_KEY", "") == "":
        return None
    try:
        client = anthropic.Anthropic()
        reply = client.messages.create(
            model="claude-haiku-5-5",
            max_tokens=1024,
            system=RULES,
            messages=[{"role": "user", "content": prompt}],
            output_config={"effort": "low"},
        )
        for block in reply.content:
            if block.type == "text":
                return block.text.strip()
    except Exception as error:
        print("Claude didn't answer:", error)
    return reply
def my_money():
    total = game["cash"]
    for c in game["companies"]:
        total = total + c["owned"] * c["price"]
    return round(total, 2)
def rita_money():
    rita = game["rita"]
    total = rita["cash"]
    for i in rita["owned"]:
        total = total + rita["owned"][i] * game["companies"][i]["price"]
    return round(total, 2)
def new_price(c, shares):
    jump = c["jump"] * shares
    if jump > 0.4:
        jump = 0.4
    if jump < -0.4:
        jump = -0.4
    return max(1.0, round(c["price"] * (1 + jump), 2))
def buy(c, amount):
    after = new_price(c, amount)
    cost = round((c["price"] + after) / 2 * amount + FEE, 2)
    if cost > game["cash"]:
        game["messages"].append("Not enough cash! That would cost $" + str(cost))
        return
    game["cash"] = round(game["cash"] - cost, 2)
    c["price"] = after
    c["owned"] = c["owned"] + amount
    game["messages"].append("You bought " + str(amount) + " " + c["name"] + " for $" + str(cost) + ". The price went up to $" + str(after))
def sell(c, amount):
    if amount > c["owned"]:
        game["messages"].append("You only have " + str(c["owned"]) + " " + c["name"])
        return
    after = new_price(c, -amount)
    money = round((c["price"] + after) / 2 * amount - FEE, 2)
    game["cash"] = round(game["cash"] + money, 2)
    c["price"] = after
    c["owned"] = c["owned"] - amount
    game["messages"].append("You sold " + str(amount) + " " + c["name"] + " for $" + str(money) + ". The price went down to $" + str(after))
def make_rumor():
    companies = game["companies"]
    alive = []
    for i in range(len(companies)):
        if not companies[i]["bankrupt"]:
            alive.append(i)
    rumor = {"true": random.random() < 0.7, "by_claude": False}
    if random.random() < 0.1 or len(alive) == 0:
        rumor["company"] = None
        about = "the whole market"
        if random.random() < 0.5:
            rumor["text"] = "MARKET CRASH! Everyone is panicking."
            rumor["effect"] = -0.3
        else:
            rumor["text"] = "BOOM TIME! The whole market is buzzing."
            rumor["effect"] = 0.15
    else:
        i = random.choice(alive)
        rumor["company"] = i
        about = companies[i]["name"] + " (" + companies[i]["product"] + ")"
        if random.random() < 0.5:
            rumor["text"] = random.choice(good_news).replace("NAME", companies[i]["name"])
            rumor["effect"] = random.uniform(0.12, 0.3)
        else:
            rumor["text"] = random.choice(bad_news).replace("NAME", companies[i]["name"])
            rumor["effect"] = -random.uniform(0.12, 0.3)
    if rumor["effect"] > 0:
        mood = "GOOD"
    else:
        mood = "BAD"
    headline = ask_claude("Write a fun news headline for the game. It must be " + mood + " news about " + about + ". Idea: " + rumor["text"] + " Reply with only the headline, one line, max 14 words, no quotes.")
    if headline is not None:
        rumor["text"] = headline.split("\n")[0].strip('" ')
        rumor["by_claude"] = True
    return rumor
def coach_tip():
    biggest = game["companies"][0]
    for c in game["companies"]:
        if c["owned"] * c["price"] > biggest["owned"] * biggest["price"]:
            biggest = c
    if my_money() < 300:
        return "Danger zone! Below $100 you're broke. Play it safe."
    if biggest["owned"] * biggest["price"] > my_money() * 0.7:
        return "Most of your money is in " + biggest["name"] + ". One crash and you could lose it all!"
    return "Spreading your money over different companies lowers your risk."
def bots():
    riser = None
    cheapest = None
    for c in game["companies"]:
        if c["bankrupt"]:
            continue
        if riser is None or c["change"] > riser["change"]:
            riser = c
        if cheapest is None or c["price"] < cheapest["price"]:
            cheapest = c
        if c["change"] < -0.05:
            c["price"] = new_price(c, -3)
            game["messages"].append("Panic Pete sold 3 " + c["name"] + " because it dropped.")
    if riser is not None and riser["change"] > 0:
        riser["price"] = new_price(riser, 3)
        game["messages"].append("Hype Hannah bought 3 " + riser["name"] + " because it went up.")
    if cheapest is not None:
        cheapest["price"] = new_price(cheapest, 2)
        game["messages"].append("Bargain Bob bought 2 " + cheapest["name"] + " because it's the cheapest.")
def rita_pick(strategy):
    companies = game["companies"]
    best = None
    for i in range(len(companies)):
        c = companies[i]
        if c["bankrupt"]:
            continue
        if best is None:
            best = i
        elif strategy == "follow the hype" and c["change"] > companies[best]["change"]:
            best = i
        elif strategy == "buy the dip" and c["change"] < companies[best]["change"]:
            best = i
        elif strategy == "play it safe" and c["jump"] < companies[best]["jump"]:
            best = i
        elif strategy == "go risky" and c["jump"] > companies[best]["jump"]:
            best = i
    return best
def rita_turn():
    rita = game["rita"]
    companies = game["companies"]
    for s in rita["scores"]:
        rita["picks"][s] = rita_pick(s)
    if rita["strategy"] == "" or random.random() < 0.25:
        rita["strategy"] = random.choice(list(rita["scores"]))
    else:
        best = "follow the hype"
        for s in rita["scores"]:
            if rita["scores"][s] > rita["scores"][best]:
                best = s
        rita["strategy"] = best
    pick = rita["picks"][rita["strategy"]]
    for i in list(rita["owned"]):
        if i != pick:
            c = companies[i]
            amount = rita["owned"][i]
            if not c["bankrupt"]:
                after = new_price(c, -amount)
                rita["cash"] = round(rita["cash"] + (c["price"] + after) / 2 * amount - FEE, 2)
                c["price"] = after
            del rita["owned"][i]
    game["messages"].append("Robo-Rita is using the strategy: " + rita["strategy"])
    if pick is None or pick in rita["owned"]:
        return
    c = companies[pick]
    amount = int(rita["cash"] * 0.5 / c["price"])
    if amount > 0:
        after = new_price(c, amount)
        cost = (c["price"] + after) / 2 * amount + FEE
        if cost <= rita["cash"]:
            rita["cash"] = round(rita["cash"] - cost, 2)
            c["price"] = after
            rita["owned"][pick] = amount
            game["messages"].append("Robo-Rita bought " + str(amount) + " " + c["name"])
def rita_learn():
    rita = game["rita"]
    for s in rita["scores"]:
        i = rita["picks"][s]
        if i is not None:
            rita["scores"][s] = rita["scores"][s] * 0.6 + game["companies"][i]["change"] * 0.4
def end_round():
    rumor = game["rumor"]
    bots()
    rita_turn()
    if rumor["true"]:
        effect = rumor["effect"]
        news = "TRUE: " + rumor["text"]
    else:
        effect = -rumor["effect"] * 0.3
        news = "FAKE: " + rumor["text"]
    companies = game["companies"]
    for i in range(len(companies)):
        c = companies[i]
        if c["bankrupt"]:
            continue
        price = c["price"]
        if rumor["company"] is None or rumor["company"] == i:
            price = price * (1 + effect)
        price = round(price * (1 + random.uniform(-c["jump"] * 2, c["jump"] * 2)), 2)
        if price < c["start"] * 0.25:
            price = 0
            c["bankrupt"] = True
            news = news + " " + c["name"] + " went BANKRUPT!"
        c["change"] = (price - c["last"]) / c["last"]
        c["price"] = price
        c["last"] = price
    rita_learn()
    game["messages"].append("NEWS: " + news)
    prices = ""
    for c in companies:
        prices = prices + c["name"] + " $" + str(c["price"]) + "  "
    game["history"].append({"round": game["round"], "news": news, "prices": prices, "money": my_money(), "rita": rita_money()})
    if my_money() >= WIN_MONEY:
        game["status"] = "won"
    elif my_money() < BROKE_MONEY:
        game["status"] = "broke"
    elif rita_money() >= WIN_MONEY:
        game["status"] = "rita won"
    elif game["round"] == ROUNDS:
        game["status"] = "finished"
    else:
        game["round"] = game["round"] + 1
        game["rumor"] = make_rumor()
game = new_game()
game["rumor"] = make_rumor()

def portfolio_data():
    stock_value = sum(c["owned"] * c["price"] for c in game["companies"])
    share_count = sum(c["owned"] for c in game["companies"])
    return {
        "balance": round(game["cash"], 2),
        "total": round(my_money(), 2),
        "stock_value": round(stock_value, 2),
        "share_count": share_count,
    }


def state_data():
    totals = portfolio_data()
    ids = ["byte", "green", "Zoomy", "PixelPlay", "rocket"]
    stocks = []
    for i, company in enumerate(game["companies"]):
        stocks.append({
            "id": ids[i],
            "name": company["name"],
            "price": round(company["price"], 2),
            "owned": company["owned"],
            "bankrupt": company["bankrupt"],
        })

    news = game["messages"][-1] if game["messages"] else "The market is open! Start trading."
    if news.startswith("NEWS: "):
        news = news[6:]

    return {
        **totals,
        "stocks": stocks,
        "news": news,
        "round": game["round"],
        "status": game["status"],
    }


@app.route("/")
def home():
    return send_from_directory(app.root_path, "index.html")


@app.route("/api/state")
def api_state():
    return jsonify(state_data())


@app.route("/api/trade", methods=["POST"])
def api_trade():
    data = request.get_json(silent=True) or {}
    company_id = str(data.get("company", ""))
    action = data.get("action", "")

    try:
        amount = int(data.get("quantity", 0))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "message": "Enter a valid number of shares."}), 400

    ids = ["byte", "green", "Zoomy", "PixelPlay", "rocket"]
    if company_id not in ids:
        return jsonify({"ok": False, "message": "Company not found."}), 404
    if amount < 1:
        return jsonify({"ok": False, "message": "Enter at least 1 share."}), 400
    if game["status"] != "playing":
        return jsonify({"ok": False, "message": "The game has ended."}), 400

    company = game["companies"][ids.index(company_id)]
    if company["bankrupt"]:
        return jsonify({"ok": False, "message": "This company is bankrupt."}), 400

    game["messages"] = []
    if action == "buy":
        buy(company, amount)
    elif action == "sell":
        sell(company, amount)
    else:
        return jsonify({"ok": False, "message": "Choose buy or sell."}), 400

    message = game["messages"][-1] if game["messages"] else "Trade completed."
    success = not message.startswith("Not enough") and not message.startswith("You only have")
    return jsonify({"ok": success, "message": message, "state": state_data()}), (200 if success else 400)


@app.route("/api/next-round", methods=["POST"])
def next_round():
    if game["status"] == "playing":
        game["messages"] = []
        end_round()
    return jsonify({"ok": True, "state": state_data()})


@app.route("/api/ai-overview", methods=["POST"])
def ai_overview():
    totals = portfolio_data()
    stock_info = ", ".join(
        f'{c["name"]}: ${c["price"]:.2f}, owned shares: {c["owned"]}'
        for c in game["companies"]
    )
    prompt = (
        "Give a short, student-friendly overview of this fictional stock market game. "
        "Explain the portfolio and remind the player that prices can rise or fall. "
        "Do not promise profits or give real-world investment advice. "
        f'Cash: ${totals["balance"]:.2f}; portfolio: ${totals["total"]:.2f}; '
        f'stock value: ${totals["stock_value"]:.2f}; shares: {totals["share_count"]}. '
        f"Stocks: {stock_info}"
    )
    overview = ask_claude(prompt)
    if overview is None:
        overview = (
            f'Your portfolio is worth ${totals["total"]:.2f}. '
            f'You have ${totals["balance"]:.2f} in cash and '
            f'${totals["stock_value"]:.2f} invested in shares. '
            f'You own {totals["share_count"]} shares. '
            "Remember that stock prices can rise or fall."
        )
    return jsonify({"ok": True, "overview": overview})


@app.route("/new", methods=["POST"])
def new():
    global game
    game = new_game()
    game["rumor"] = make_rumor()
    return redirect("/")


if __name__ == "__main__":
    app.run(debug=True)
