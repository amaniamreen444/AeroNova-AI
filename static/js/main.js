function toggleChatbot() {

    const chatbot =
        document.getElementById("chatbotWindow");

    chatbot.classList.toggle("active");
}


function handleChatKey(event) {

    if (event.key === "Enter") {
        sendMessage();
    }

}


function quickMessage(message) {

    document.getElementById("chatInput").value = message;

    sendMessage();

}


function swapCities() {

    const origin =
        document.querySelector(
            'input[name="origin"]'
        );

    const destination =
        document.querySelector(
            'input[name="destination"]'
        );

    const temporaryValue = origin.value;

    origin.value = destination.value;

    destination.value = temporaryValue;

}


async function sendMessage() {

    const input =
        document.getElementById("chatInput");

    const message =
        input.value.trim();

    if (!message) return;


    const chatMessages =
        document.getElementById("chatMessages");


    // User message

    const userMessage =
        document.createElement("div");

    userMessage.className =
        "user-message";

    userMessage.textContent =
        message;

    chatMessages.appendChild(userMessage);

    input.value = "";


    // Temporary reply

    const thinking =
        document.createElement("div");

    thinking.className =
        "bot-message";

    thinking.textContent =
        "AeroNova AI is thinking... ✈️";

    chatMessages.appendChild(thinking);

    chatMessages.scrollTop =
        chatMessages.scrollHeight;


    try {

        const response =
            await fetch("/api/chat", {

                method: "POST",

                headers: {
                    "Content-Type":
                        "application/json"
                },

                body: JSON.stringify({
                    message: message
                })

            });


        const data =
            await response.json();


        thinking.remove();


        const botReply =
            document.createElement("div");

        botReply.className =
            "bot-message";

        botReply.textContent =
            data.reply ||
            "Sorry, I could not understand that.";

        chatMessages.appendChild(botReply);


    }
    catch (error) {

        thinking.remove();


        const botReply =
            document.createElement("div");

        botReply.className =
            "bot-message";

        botReply.textContent =
            "🤖 AeroNova AI is not connected yet. We will connect the AI API in a later phase.";

        chatMessages.appendChild(botReply);

    }


    chatMessages.scrollTop =
        chatMessages.scrollHeight;

}