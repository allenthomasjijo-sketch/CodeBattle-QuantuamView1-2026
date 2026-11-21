const inputIds = {
    byte: "byteQty",
    green: "greenQty",
    Zoomy: "ZoomQant",
    PixelPlay: "pixelQty",
    rocket: "rocketrQant"
};

const ownedIds = {
    byte: "byteOwned",
    green: "greenOwned",
    Zoomy: "ZoomOwned",
    PixelPlay: "pixelOwned",
    rocket: "rocketrOwned"
};

function showTradeMessage(message) {
    let output = document.getElementById("tradeMessage");
    if (!output) {
        output = document.createElement("p");
        output.id = "tradeMessage";
        output.style.color = "#22C55E";
        output.style.fontWeight = "bold";
        output.style.marginTop = "10px";
        document.getElementById("Buy").appendChild(output);
    }
    output.textContent = message;
}

async function refreshPortfolio() {
    const response = await fetch("/api/state");
    const data = await response.json();

    document.getElementById("balance").textContent = "$" + data.balance.toFixed(2);
    document.getElementById("total").textContent = "$" + data.total.toFixed(2);
    document.getElementById("stotal").textContent = "$" + data.stock_value.toFixed(2);
    document.getElementById("sntotal").textContent = data.share_count;
    document.getElementById("news").textContent = data.news;

    const roundEl = document.getElementById("roundNum");
    if (roundEl) roundEl.textContent = data.round;

    const cards = document.querySelectorAll("#Buy .stock-card");
    data.stocks.forEach((stock, index) => {
        if (cards[index]) {
            const priceHeading = cards[index].querySelector("h2");
            priceHeading.textContent = stock.bankrupt
                ? "BANKRUPT ($0.00)"
                : "$" + stock.price.toFixed(2);
        }
        const ownedElement = document.getElementById(ownedIds[stock.id]);
        if (ownedElement) ownedElement.textContent = stock.owned;
    });

    if (data.status && data.status !== "playing") {
        showTradeMessage("Game status: " + data.status.toUpperCase() + ".");
    }
}

async function trade(company, action) {
    const quantity = Number(document.getElementById(inputIds[company]).value);

    if (!Number.isInteger(quantity) || quantity < 1) {
        showTradeMessage("Enter a whole number of shares greater than zero.");
        return;
    }

    try {
        const response = await fetch("/api/trade", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({company, action, quantity})
        });
        const result = await response.json();
        showTradeMessage(result.message || "Trade could not be completed.");
        await refreshPortfolio();
    } catch (error) {
        showTradeMessage("Could not connect. Make sure the Flask server is running.");
    }
}

async function nextRound() {
    try {
        const response = await fetch("/api/next-round", {method: "POST"});
        const result = await response.json();
        if (result.ok) {
            showTradeMessage("Round updated! Check the latest market news and prices.");
            await refreshPortfolio();
        }
    } catch (error) {
        showTradeMessage("Could not advance round. Make sure the Flask server is running.");
    }
}

async function newGame() {
    try {
        await fetch("/new", {method: "POST"});
        showTradeMessage("New game started!");
        await refreshPortfolio();
    } catch (error) {
        showTradeMessage("Could not start a new game. Make sure the Flask server is running.");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const aiButton = document.getElementById("getai");
    if (aiButton) {
        aiButton.addEventListener("click", async () => {
            const output = document.getElementById("aiOverview");
            if (output) output.textContent = "Generating overview...";
            try {
                const response = await fetch("/api/ai-overview", {method: "POST"});
                const result = await response.json();
                if (output) output.textContent = result.overview;
            } catch (error) {
                if (output) output.textContent = "Could not connect to the Python server.";
            }
        });
    }
    refreshPortfolio();
});
