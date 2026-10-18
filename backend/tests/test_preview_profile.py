import pytest
from fastapi.testclient import TestClient

from app.agents.interview_agent import ProfileDraft
from app.api import interview_routes
from app.api.main import app


@pytest.fixture(autouse=True)
def fake_agent(monkeypatch):
    interview_routes._preview_used.clear()

    class FakeAgent:
        async def draft_profile(self, memo, messages):
            assert messages == []
            return ProfileDraft(name="펫가드", customer="직장인 반려인")

    monkeypatch.setattr(interview_routes, "InterviewAgent", FakeAgent)


def test_preview_once_per_ip_per_day():
    client = TestClient(app)
    h = {"x-forwarded-for": "1.2.3.4, 10.0.0.1"}
    first = client.post("/api/v1/interview/preview-profile", json={"memo": "펫 CCTV"}, headers=h)
    assert first.status_code == 200 and first.json()["name"] == "펫가드"
    second = client.post("/api/v1/interview/preview-profile", json={"memo": "다른 메모"}, headers=h)
    assert second.status_code == 429
    other = client.post("/api/v1/interview/preview-profile", json={"memo": "펫 CCTV"}, headers={"x-forwarded-for": "5.6.7.8"})
    assert other.status_code == 200


def test_failure_does_not_use_quota(monkeypatch):
    class Boom:
        async def draft_profile(self, memo, messages):
            raise RuntimeError("llm down")

    monkeypatch.setattr(interview_routes, "InterviewAgent", Boom)
    client = TestClient(app)
    h = {"x-forwarded-for": "9.9.9.9"}
    assert client.post("/api/v1/interview/preview-profile", json={"memo": "m"}, headers=h).status_code == 502
    assert "9.9.9.9" not in interview_routes._preview_used
