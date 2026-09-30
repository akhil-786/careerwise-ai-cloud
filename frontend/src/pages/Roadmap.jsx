import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { generateRoadmap } from "../services/api";

const roadmapStages = [
  {
    number: 1,
    title: "Cloud Fundamentals & Certification",
    shortTitle: "Cloud Fundamentals",
    duration: "1–2 months",
    description:
      "Build a solid foundation in cloud computing concepts and earn a foundational certification.",
    topics: [
      "Cloud concepts & terminology",
      "AWS / Azure / GCP basics",
      "Core services overview",
      "Cloud Practitioner certification",
    ],
    outcome: "Understand cloud basics and get certified",
    color: "blue",
  },
  {
    number: 2,
    title: "Core Services & Scripting",
    shortTitle: "Core Services & Scripting",
    duration: "2–3 months",
    description:
      "Dive deeper into essential cloud services and learn to interact with them using scripting.",
    topics: [
      "Compute, storage, networking",
      "Python or Bash scripting",
      "Cloud CLI and SDKs",
      "Hands-on lab exercises",
    ],
    outcome: "Work with core cloud services programmatically",
    color: "green",
  },
  {
    number: 3,
    title: "Infrastructure as Code",
    shortTitle: "Infrastructure as Code",
    duration: "2–3 months",
    description:
      "Learn to provision and manage cloud resources programmatically using Infrastructure as Code.",
    topics: [
      "Terraform or CloudFormation",
      "Version control with Git",
      "Automated infrastructure",
      "Environment management",
    ],
    outcome: "Build and manage infrastructure with code",
    color: "orange",
  },
  {
    number: 4,
    title: "Containerization & CI/CD",
    shortTitle: "Containers & CI/CD",
    duration: "2–3 months",
    description:
      "Learn container technologies and continuous integration and continuous deployment pipelines.",
    topics: [
      "Docker fundamentals",
      "Kubernetes basics",
      "CI/CD pipelines",
      "Deployment automation",
    ],
    outcome: "Containerize and deploy applications",
    color: "purple",
  },
  {
    number: 5,
    title: "Projects & Specialization",
    shortTitle: "Projects & Specialization",
    duration: "Ongoing",
    description:
      "Build real-world projects and develop deeper expertise in areas based on your interests.",
    topics: [
      "End-to-end cloud projects",
      "Security and monitoring",
      "Cost optimization",
      "Choose a specialization",
    ],
    outcome: "Build a strong portfolio and become job-ready",
    color: "red",
  },
];

function Roadmap() {
  const navigate = useNavigate();
  const recommendationId = sessionStorage.getItem("careercloud_recommendationId");

  const [roadmap, setRoadmap] = useState(null);
  const [loading, setLoading] = useState(Boolean(recommendationId));
  const [error, setError] = useState(recommendationId ? "" : "Recommendation information not found.");

  useEffect(() => {
    if (!recommendationId) return;

    const createRoadmap = async () => {
      try {
        const response = await generateRoadmap(recommendationId);

        console.log("Roadmap response:", response);

        setRoadmap(response);

        if (response.roadmap?.roadmapId) {
          sessionStorage.setItem(
            "careercloud_roadmapId",
            response.roadmap.roadmapId
          );
        }
      } catch (err) {
        console.error(err);
        setError("Unable to generate your learning roadmap.");
      } finally {
        setLoading(false);
      }
    };

    createRoadmap();
  }, [recommendationId]);

  if (loading) {
    return (
      <div className="roadmap-page loading-roadmap">
        <div className="roadmap-loading-card">
          <div className="roadmap-loader"></div>

          <span className="roadmap-eyebrow">AI LEARNING ROADMAP</span>

          <h1>Building your career path...</h1>

          <p>
            CareerCloud AI is creating a personalized learning journey based
            on your career recommendation.
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="roadmap-page">
        <div className="roadmap-error-card">
          <h2>Something went wrong</h2>

          <p>{error}</p>

          <button onClick={() => navigate("/recommendation")}>
            ← Back to Recommendation
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="roadmap-page">
      {/* Header */}
      <div className="roadmap-container">
        <button
          className="back-button"
          onClick={() => navigate("/recommendation")}
        >
          ← Back to Recommendation
        </button>

        <div className="roadmap-header">
          <div>
            <span className="roadmap-eyebrow">LEARNING ROADMAP</span>

            <h1>
              Your Path to Cloud Engineer / DevOps Engineer
            </h1>

            <p>
              Here's a personalized learning roadmap to help you build the
              skills and knowledge needed for your target career. Follow this
              path step by step to achieve your goal.
            </p>
          </div>

          <div className="goal-card">
            <div className="goal-icon">🎯</div>

            <div>
              <span>Your Goal</span>

              <strong>
                Cloud Engineer / DevOps Engineer
              </strong>
            </div>

            <p>
              "From where you are today, to a successful career in the cloud."
            </p>
          </div>
        </div>

        {/* Graphical Road */}
        <div className="roadmap-visual">
          <div className="mountains"></div>

          <div className="road"></div>

          <div className="start-marker">
            <div className="sign">Start Here</div>
          </div>

          {roadmapStages.map((stage) => (
            <div
              key={stage.number}
              className={`map-marker marker-${stage.number}`}
            >
              <div className="map-label">
                <strong>{stage.shortTitle}</strong>
                <span>{stage.duration}</span>
              </div>

              <div className={`marker-pin ${stage.color}`}>
                {stage.number}
              </div>
            </div>
          ))}

          <div className="goal-marker">
            <div className="goal-sign">Your Goal 🚩</div>
          </div>
        </div>

        {/* Stage Cards */}
        <div className="roadmap-stages">
          {roadmapStages.map((stage) => (
            <div
              key={stage.number}
              className={`stage-card ${stage.color}`}
            >
              <div className="stage-number">
                {stage.number}
              </div>

              <h2>{stage.title}</h2>

              <span className="duration">
                {stage.duration}
              </span>

              <p>{stage.description}</p>

              <div className="topics">
                <h3>Key Topics</h3>

                <ul>
                  {stage.topics.map((topic) => (
                    <li key={topic}>
                      <span>✓</span>
                      {topic}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="outcome">
                <strong>🏆 Outcome</strong>

                <p>{stage.outcome}</p>
              </div>
            </div>
          ))}
        </div>

        {/* AI Response */}
        {roadmap?.roadmap?.roadmap && (
          <div className="ai-roadmap">
            <span className="roadmap-eyebrow">
              AI-GENERATED PLAN
            </span>

            <h2>Your Personalized AI Roadmap</h2>

            <div className="ai-roadmap-content">
              {roadmap.roadmap.roadmap}
            </div>
          </div>
        )}

        <div className="journey-button-container">
          <button className="journey-button">
            🚀 Start My Learning Journey →
          </button>

          <p>
            Each step builds on the previous one. Take your time and enjoy the
            journey!
          </p>
        </div>
      </div>
    </div>
  );
}

export default Roadmap;
