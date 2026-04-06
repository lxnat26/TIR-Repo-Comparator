import os
from crewai import Agent, Task, Crew, LLM

# 1. Configuration: Connect to your LOCAL Ollama Vision Model
# Make sure you ran 'ollama pull llama3.2-vision' first!
vision_llm = LLM(
    model="ollama/llama3.2-vision",
    base_url="http://localhost:11434"
)

# 2. Define the Specialist Agent
image_analyst = Agent(
    role="Pharmaceutical Data Analyst",
    goal="Extract and summarize clinical data from charts and tables.",
    backstory="""You are an expert at reading medical research graphs. 
    You identify drug names, dosages, and efficacy percentages (like p-values or PFS).
    You turn complex visuals into clear, 2-sentence summaries.""",
    llm=vision_llm,
    allow_delegation=False
)

def process_report_images(markdown_file, image_folder):
    # Read the markdown file created in Step 2
    with open(markdown_file, "r") as f:
        content = f.read()

    # Look for all image files in the extracted folder
    images = [f for f in os.listdir(image_folder) if f.endswith(('.png', '.jpg', '.jpeg'))]
    
    print(f"Found {len(images)} images to analyze...")

    for img in images:
        img_path = os.path.join(image_folder, img)
        
        # 3. Create the Task for this specific image
        analysis_task = Task(
            description=f"Analyze this image: {img_path}. What data does it show regarding the trial results?",
            expected_output="A brief, professional summary of the chart's key data point.",
            agent=image_analyst
        )

        # 4. Run the Crew
        crew = Crew(agents=[image_analyst], tasks=[analysis_task])
        print(f"--- Analyzing {img} ---")
        result = crew.kickoff()

        # 5. Update the Markdown: Replace the [PENDING] tag with the real data
        # Note: We look for the image filename in the markdown to find the right spot
        placeholder = f"![Analysis Needed]({img})"
        if placeholder in content:
            interpretation = f"\n**AI Analysis:** {result}\n"
            content = content.replace("> [PENDING AI INTERPRETATION]", interpretation, 1)

    # Save the 'Enriched' Markdown
    with open(markdown_file, "w") as f:
        f.write(content)
    
    print("--- Report Enrichment Complete! ---")

# To test:
# process_report_images("processed_reports/your_report.md", "processed_reports/images")