from components.test_data import TEST_MEETINGS


def fetch_meeting_details(meeting_id):
    meeting = next((m for m in TEST_MEETINGS if m["id"] == meeting_id), None)
    return meeting
