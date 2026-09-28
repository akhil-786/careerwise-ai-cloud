const API_BASE_URL = "/api";

// Create User
export async function createUser(userData) {
  const response = await fetch(`${API_BASE_URL}/users`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(userData),
  });

  if (!response.ok) {
    throw new Error("Failed to create user");
  }

  return response.json();
}

// Get User
export async function getUser(userId) {
  const response = await fetch(`${API_BASE_URL}/users/${userId}`);

  if (!response.ok) {
    throw new Error("Failed to get user");
  }

  return response.json();
}

// Submit Assessment
export async function submitAssessment(assessmentData) {
  const response = await fetch(`${API_BASE_URL}/assessment`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(assessmentData),
  });

  if (!response.ok) {
    throw new Error("Failed to submit assessment");
  }

  return response.json();
}

// Generate Career Recommendation
export async function generateRecommendation(assessmentId) {
    const response = await fetch(`${API_BASE_URL}/recommendation`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        assessmentId,
      }),
    });
  
    const responseText = await response.text();
  
    console.log("Recommendation status:", response.status);
    console.log("Recommendation response:", responseText);
  
    if (!response.ok) {
      throw new Error(
        `Recommendation API failed: ${response.status} ${responseText}`
      );
    }
  
    return JSON.parse(responseText);
  }

// Generate Learning Roadmap
export async function generateRoadmap(recommendationId) {
  const response = await fetch(`${API_BASE_URL}/roadmap`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      recommendationId,
    }),
  });

  if (!response.ok) {
    throw new Error("Failed to generate roadmap");
  }

  return response.json();
}