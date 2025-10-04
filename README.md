### Tiny AI QnA Bot



Ask anything, get answers from an AI—right in your browser or terminal!  

Fast, flexible, deployable.

A simple, command-line AI-powered chat application built for an internship assignment. [cite_start]The goal was to demonstrate effort, resourcefulness, and creativity by building a simple AI app in a short timeframe[cite: 3, 4].

---

## Features

* **Interactive Chat**: Engage in a back-and-forth conversation directly from your terminal.
* [cite_start]**AI-Powered Answers**: Leverages the `google/flan-t5-base` model via the Hugging Face Inference API to answer a wide range of questions[cite: 12].
* **Engaging UI**: Includes a creative "boot-up" sequence and "thinking" indicators to improve the user experience.

---

## Tech Stack

* **Language**: Python 3
* **API**: Hugging Face Inference API
* **Core Libraries**:
    * `requests`: For making HTTP requests to the API.
    * `python-dotenv`: For securely managing the API key.
    * `time`: For creating a more dynamic user experience.

---

## ⚙️ Setup and Installation

To run this project locally, follow these steps:

1.  **Clone the repository:**
    ```bash
    git clone [Your GitHub Repo URL]
    cd [Your Repo Name]
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up your API Key:**
    * Create a file named `.env` in the root of the project.
    * Add your Hugging Face API key to the file like this:
        ```
        HF_API_KEY="hf_YourApiKeyHere"
        ```

5.  **Run the application:**
    ```bash
    python main.py
    ```

---

## The Approach

This section documents the steps and thought process behind building the app.

### Core Functionality & Setup

* [cite_start]**Objective**: Build a working command-line Q&A application[cite: 11].
* **Process**:
    1.  Chose the "AI Q&A Bot" project because it seemed like the best way to showcase API integration and creativity.
    2.  [cite_start]Set up a local Python environment and a GitHub repository[cite: 7].
    3.  Wrote the initial script (`main.py`) to handle user input in a loop.
    4.  Integrated the Hugging Face API to provide answers.
    5.  The first version was functional but very basic. I decided to improve the user experience by adding more creative print statements, a simulated "boot-up" sequence, and a "thinking" indicator to make the app feel more alive. [cite_start]This was a small touch to go beyond the minimum requirements[cite: 24].
    6.  Implemented `python-dotenv` to handle the API key securely, which is a better practice than hardcoding it. [cite_start]This was something I learned while researching how to handle secrets in Python projects[cite: 23].

*(This journey will be updated as the project progresses)*

