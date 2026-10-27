document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const loginToggle = document.getElementById("teacher-login-toggle");
  const loginForm = document.getElementById("teacher-login-form");
  const teacherSession = document.getElementById("teacher-session");
  const teacherName = document.getElementById("teacher-name");
  const authMessage = document.getElementById("auth-message");
  const publicViewNote = document.getElementById("public-view-note");
  let isTeacher = false;

  function showAuthMessage(text, isError = false) {
    authMessage.textContent = text;
    authMessage.className = isError ? "error" : "success";
  }

  function updateTeacherControls(username = "") {
    isTeacher = Boolean(username);
    document.getElementById("signup-container").classList.toggle("hidden", !isTeacher);
    document.querySelectorAll(".delete-btn").forEach((button) => {
      button.classList.toggle("hidden", !isTeacher);
    });
    loginToggle.classList.toggle("hidden", isTeacher);
    loginForm.classList.add("hidden");
    loginToggle.setAttribute("aria-expanded", "false");
    teacherSession.classList.toggle("hidden", !isTeacher);
    publicViewNote.classList.toggle("hidden", isTeacher);
    teacherName.textContent = username;
  }

  async function checkTeacherSession() {
    try {
      const response = await fetch("/auth/me");
      const session = await response.json();
      updateTeacherControls(session.authenticated ? session.username : "");
    } catch (error) {
      updateTeacherControls();
      console.error("Error checking teacher session:", error);
    }
  }

  // Function to fetch activities from API
  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      const activities = await response.json();

      // Clear loading message
      activitiesList.innerHTML = "";
      activitySelect.replaceChildren(new Option("-- Select an activity --", ""));

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft =
          details.max_participants - details.participants.length;

        // Create participants HTML with delete icons instead of bullet points
        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map(
                    (email) =>
                      `<li><span class="participant-email">${email}</span><button class="delete-btn" data-activity="${name}" data-email="${email}">❌</button></li>`
                  )
                  .join("")}
              </ul>
            </div>`
            : `<p><em>No participants yet</em></p>`;

        activityCard.innerHTML = `
          <h4>${name}</h4>
          <p>${details.description}</p>
          <p><strong>Schedule:</strong> ${details.schedule}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;

        activitiesList.appendChild(activityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      // Add event listeners to delete buttons
      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
        button.classList.toggle("hidden", !isTeacher);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  // Handle unregister functionality
  async function handleUnregister(event) {
    const button = event.target;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
        }
      );

      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        messageDiv.textContent = response.status === 401
          ? "Please sign in as a teacher to manage registrations."
          : result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to unregister. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error unregistering:", error);
    }
  }

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
        }
      );

      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";
        signupForm.reset();

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        messageDiv.textContent = response.status === 401
          ? "Please sign in as a teacher to manage registrations."
          : result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to sign up. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error signing up:", error);
    }
  });

  loginToggle.addEventListener("click", () => {
    const isExpanded = loginToggle.getAttribute("aria-expanded") === "true";
    loginToggle.setAttribute("aria-expanded", String(!isExpanded));
    loginForm.classList.toggle("hidden", isExpanded);
    if (!isExpanded) {
      document.getElementById("teacher-username").focus();
    }
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(loginForm);

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: formData.get("username"),
          password: formData.get("password"),
        }),
      });
      const result = await response.json();

      if (!response.ok) {
        showAuthMessage(result.detail || "Unable to sign in.", true);
        return;
      }

      loginForm.reset();
      authMessage.classList.add("hidden");
      updateTeacherControls(result.username);
      await fetchActivities();
    } catch (error) {
      showAuthMessage("Unable to sign in. Please try again.", true);
      console.error("Error signing in:", error);
    }
  });

  document.getElementById("teacher-logout").addEventListener("click", async () => {
    try {
      await fetch("/auth/logout", { method: "POST" });
      updateTeacherControls();
      await fetchActivities();
      showAuthMessage("You have signed out.");
    } catch (error) {
      showAuthMessage("Unable to sign out. Please try again.", true);
      console.error("Error signing out:", error);
    }
  });

  async function initializeApp() {
    await checkTeacherSession();
    await fetchActivities();
  }

  initializeApp();
});
