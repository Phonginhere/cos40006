import streamlit as st
import json
import openai

# Load OpenAI API key from a separate text file
def load_api_key():
    try:
        with open("openai_api_key.txt", "r") as file:
            return file.read().strip()
    except FileNotFoundError:
        st.error("API key file not found. Please create 'openai_api_key.txt' and add your API key.")
        return None

openai.api_key = load_api_key()

# Function to process persona data into readable text
def process_persona(persona):
    return f"""
    Name: {persona['Name']}
    Age: {persona['Age']}
    Location: {persona['Location']}
    Occupation: {persona['Occupation']}
    Marital Status: {persona['Marital_Status']}
    Education: {persona['Education']}
    Technology Comfort Level: {persona['Technology_Comfort_Level']}

    Goals:
{chr(10).join(f"- {goal}" for goal in persona['Goals'])}

    Challenges:
{chr(10).join(f"- {challenge}" for challenge in persona['Challenges'])}

    Frustrations:
{chr(10).join(f"- {frustration}" for frustration in persona['Frustrations'])}

    Preferred Device Technology:
{chr(10).join(f"- {tech}" for tech in persona['Preferred_Device_Technology'])}

    Key Features Desired:
{chr(10).join(f"- {feature}" for feature in persona['Key_Features_Desired'])}
    """

# Generate SRD for each persona
def generate_srd(persona_name, persona_text, context_responses=[]):
    context = "\n".join([f"   {i+1}: {response}" for i, response in enumerate(context_responses)])

    llm_prompt = f"""
    Based on the following persona and context:

    Persona:
    {persona_text}

    Context:
    {context}

    Generate a text-based detailed, informative and comprehensive system requirements document that addresses the needs and goals of the users described in the context. Ensure the structure of the system requirements document includes the following chapters:

    **Chapter 1: Introduction**
    - Outline the purpose, scope, context, status, and target audience of this deliverable. Describe the goals of the system and explain how it will serve the needs and challenges outlined in the context.

    **Chapter 2: Definition of User Stories and Methods**
    - Define the methods used for identifying user stories, including how user needs were gathered (e.g., focus groups, interviews). Describe the main pillars guiding the system design and the target groups. Include an insight into the methods used for gathering and analyzing user data.

    **Chapter 3: Overview of Existing User Requirements**
    - Provide an overview of existing user requirements from related literature, studies, or projects relevant to the design of the system for healthy and active aging. Discuss how these requirements align with or differ from the user stories provided in the context.

    **Chapter 4: Use Cases and Personas**
    - Define the use cases and personas that have been verified with the gathered user data. Describe key use cases that represent typical user interactions with the system, and include detailed personas representing different user types based on the provided context.

    **Chapter 5: User Stories (Functional and Non-functional Requirements)**
    - Define the user stories, focusing on both functional and non-functional requirements. Functional requirements should specify what the system must do, while non-functional requirements should outline performance, usability, security, and other quality aspects. Ensure that these requirements align with the user goals, challenges, and key features described in the context.

    **Chapter 6: Conclusion**
    - Summarize the findings of the SRD. Highlight how the system requirements fulfill the goals of the users and address the needs, challenges, and desired features identified in the context. Provide an overview of next steps for system development.

    Importantly, ensure the requirements address the users' needs, goals, challenges, and key features as described in the context
    """

    response = openai.chat.completions.create(
        model="gpt-4o-mini",  # Use GPT-4
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": llm_prompt},
        ],
        max_tokens=8192,  # Adjust this based on how much detail you want
        temperature=0.8,  # Adjust for creativity; lower is more deterministic
        n=1  # Generate 1 response
    )

    generated_srd = response.choices[0].message.content.strip()

    return generated_srd

st.title("SRD Generator")

uploaded_file = st.file_uploader("Upload a User Persona JSON file", type=["json"])

if uploaded_file:
    persona_data = json.load(uploaded_file)
    processed_persona = process_persona(persona_data)
    
    st.subheader("Generated Software Requirements Document (SRD)")
    srd_text = generate_srd(persona_data['Name'], processed_persona)
    st.text_area("Software Requirements Document", srd_text, height=400)
    
    # Provide a download link for the SRD
    st.download_button(label="Download SRD as Text File", 
                       data=srd_text, 
                       file_name="software_requirements.txt", 
                       mime="text/plain")
