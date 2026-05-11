import pytest
import copy
from fastapi.testclient import TestClient
from src.app import app, activities

# Original activities data for resetting
ORIGINAL_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Debate Club": {
        "description": "Develop public speaking and critical thinking skills through debate",
        "schedule": "Wednesdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": []
    }
}


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to original state before each test"""
    activities.clear()
    activities.update(copy.deepcopy(ORIGINAL_ACTIVITIES))


def test_root_redirect(client):
    """Test root endpoint redirects to static index"""
    response = client.get("/")
    assert response.status_code == 200  # TestClient follows redirects
    # Could check content-type or content, but for now just status


def test_get_activities(client):
    """Test getting all activities"""
    response = client.get("/activities")
    assert response.status_code == 200
    data = response.json()

    # Check structure
    assert isinstance(data, dict)
    assert len(data) == 4
    assert "Chess Club" in data
    assert "Programming Class" in data
    assert "Gym Class" in data
    assert "Debate Club" in data

    # Check each activity has required fields
    for activity_name, activity_data in data.items():
        assert "description" in activity_data
        assert "schedule" in activity_data
        assert "max_participants" in activity_data
        assert "participants" in activity_data
        assert isinstance(activity_data["participants"], list)

    # Check specific data
    chess_club = data["Chess Club"]
    assert chess_club["max_participants"] == 12
    assert len(chess_club["participants"]) == 2
    assert "michael@mergington.edu" in chess_club["participants"]

    debate_club = data["Debate Club"]
    assert debate_club["participants"] == []


def test_signup_success(client):
    """Test successful signup"""
    response = client.post("/activities/Debate%20Club/signup?email=test@mergington.edu")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "Signed up test@mergington.edu for Debate Club" in data["message"]

    # Verify participant was added
    response = client.get("/activities")
    activities_data = response.json()
    assert "test@mergington.edu" in activities_data["Debate Club"]["participants"]


def test_signup_activity_not_found(client):
    """Test signup for non-existent activity"""
    response = client.post("/activities/NonExistent/signup?email=test@mergington.edu")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Activity not found"


def test_signup_already_signed_up(client):
    """Test signup when already enrolled"""
    # First signup
    client.post("/activities/Debate%20Club/signup?email=test@mergington.edu")

    # Try again
    response = client.post("/activities/Debate%20Club/signup?email=test@mergington.edu")
    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Student already signed up for this activity"


def test_signup_multiple_students(client):
    """Test multiple students signing up for same activity"""
    client.post("/activities/Debate%20Club/signup?email=student1@mergington.edu")
    client.post("/activities/Debate%20Club/signup?email=student2@mergington.edu")

    response = client.get("/activities")
    activities_data = response.json()
    participants = activities_data["Debate Club"]["participants"]
    assert len(participants) == 2
    assert "student1@mergington.edu" in participants
    assert "student2@mergington.edu" in participants


def test_unregister_success(client):
    """Test successful unregister"""
    # First signup
    client.post("/activities/Debate%20Club/signup?email=test@mergington.edu")

    # Then unregister
    response = client.delete("/activities/Debate%20Club/signup?email=test@mergington.edu")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "Unregistered test@mergington.edu from Debate Club" in data["message"]

    # Verify participant was removed
    response = client.get("/activities")
    activities_data = response.json()
    assert "test@mergington.edu" not in activities_data["Debate Club"]["participants"]


def test_unregister_activity_not_found(client):
    """Test unregister from non-existent activity"""
    response = client.delete("/activities/NonExistent/signup?email=test@mergington.edu")
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Activity not found"


def test_unregister_not_signed_up(client):
    """Test unregister when not enrolled"""
    response = client.delete("/activities/Debate%20Club/signup?email=test@mergington.edu")
    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Student not signed up for this activity"


def test_unregister_from_existing_participants(client):
    """Test unregistering from activity with existing participants"""
    # Chess Club has 2 participants initially
    response = client.delete("/activities/Chess%20Club/signup?email=michael@mergington.edu")
    assert response.status_code == 200

    # Verify only one remains
    response = client.get("/activities")
    activities_data = response.json()
    participants = activities_data["Chess Club"]["participants"]
    assert len(participants) == 1
    assert "daniel@mergington.edu" in participants
    assert "michael@mergington.edu" not in participants


def test_signup_unregister_integration(client):
    """Test full signup -> verify -> unregister -> verify cycle"""
    # Signup
    client.post("/activities/Debate%20Club/signup?email=integration@mergington.edu")

    # Verify added
    response = client.get("/activities")
    assert "integration@mergington.edu" in response.json()["Debate Club"]["participants"]

    # Unregister
    client.delete("/activities/Debate%20Club/signup?email=integration@mergington.edu")

    # Verify removed
    response = client.get("/activities")
    assert "integration@mergington.edu" not in response.json()["Debate Club"]["participants"]


def test_case_sensitive_emails(client):
    """Test that emails are case-sensitive"""
    # Signup with lowercase
    client.post("/activities/Debate%20Club/signup?email=test@mergington.edu")

    # Try signup with uppercase (should work)
    response = client.post("/activities/Debate%20Club/signup?email=TEST@mergington.edu")
    assert response.status_code == 200

    # Check both are in list
    response = client.get("/activities")
    participants = response.json()["Debate Club"]["participants"]
    assert "test@mergington.edu" in participants
    assert "TEST@mergington.edu" in participants


def test_empty_email_handling(client):
    """Test handling of empty email parameter"""
    # Empty email should still be processed (no validation)
    response = client.post("/activities/Debate%20Club/signup?email=")
    assert response.status_code == 200

    # Verify empty string was added
    response = client.get("/activities")
    participants = response.json()["Debate Club"]["participants"]
    assert "" in participants