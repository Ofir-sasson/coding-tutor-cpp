# 🚀 Production Trap Simulator

**Project:** Agent-Based Simulator for Real-World Industry Scenarios

## 📋 Overview
The **Production Trap Simulator** is an interactive, agentic workflow designed to bridge the gap between academic coding and the high-pressure realities of software production. Unlike standard coding exercises, this system acts as a "problem generator," placing the student in a realistic lifecycle of a production failure. The simulation forces users to navigate ambiguous requirements, professional friction, and critical system outages that generic AI tools struggle to solve in a single step.

---

## 🤖 Multi-Agent Architecture
The system is built using **LangGraph** to manage a stateful, cyclic workflow involving distinct professional personas:

* **Senior Team Lead Node**: Focuses on functional requirements. This agent simulates the common industry pitfall of approving code that "works" but isn't "production-ready," eventually triggering a deployment to production.
* **Production Monitor Node**: Acts as the automated alerting system. It detects critical failures—such as database locks or API rate limits—and reports them as high-priority incidents.
* **Software Architect Node**: Conducts the post-mortem analysis. This agent is strict and requires the student to implement specific architectural patterns (e.g., non-blocking DDL, caching) before the task is marked as "Solved".

---

## 🧠 Strategic Design: AI-Resistance & Scalability
To satisfy the pedagogical goals of the assignment, the simulator implements several "AI-Resistant" strategies:

* **Dynamic Scenario Mutation (Scale)**: The `ScenarioManager` leverages a generative model to mutate base scenarios. By varying table names, variable identifiers, and tech-stack specifics for every run, the system ensures that 60+ students cannot simply share solutions.
* **Human-in-the-Loop Pressure**: The agents are designed to simulate interpersonal dynamics, such as a "nitpicking" reviewer or a stressed manager, forcing students to justify their technical decisions under pressure.
* **Contextual Dependency**: Success requires understanding the unique "incident report" generated during the `production_crash` phase. A simple copy-paste into an LLM often fails because the "bug" is only visible through the simulator's specific production logs.

---

## 🛠 Technical Stack
* **Core Logic**: Python 3.10+.
* **Orchestration**: `LangGraph` for stateful transitions and interruptible flows.
* **Memory Management**: `TypedDict` and `MemorySaver` to track attempts and message history across phases.
* **Models**: Integration with GPT-4o for deterministic yet adaptive agent responses.

---

## 🎮 How to Run
1.  **Environment**: Ensure you have your `OPENAI_API_KEY` in a `.env` file.
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Execute**:
    ```bash
    python main.py
    ```

---

## 🎯 Educational Objectives
* **Beyond Syntax**: Teaches students to think about system stability and production risks, not just logic.
* **Incident Response**: Provides a safe environment to practice debugging "Ghost-in-the-machine" bugs.
* **Professional Communication**: Simulates the nuances of code reviews and technical justification in a corporate environment.

---

**"Bridging the gap between the classroom and the industry through agentic simulation."** 