"""Unit tests for dashboard_app.py SQL helper functions."""
import pytest
from datetime import datetime, timedelta
import pandas as pd
from scripts.dashboard_app import df_review_trends, df_agent_volume

def test_df_review_trends(pg):
    """Test review trends dataframe generation."""
    # Insert test data
    with pg() as conn:
        with conn.cursor() as cur:
            # Add reviews across different dates
            cur.execute("""
                INSERT INTO reviews (created_at, agent_id, conversation_id, rating)
                VALUES 
                    (now() - interval '5 days', 'agent1', 'conv1', 5),
                    (now() - interval '4 days', 'agent1', 'conv2', 4),
                    (now() - interval '3 days', 'agent2', 'conv3', 3),
                    (now() - interval '2 days', 'agent2', 'conv4', 5),
                    (now() - interval '1 day', 'agent1', 'conv5', 5)
            """)
    
    # Test review trends for last 7 days
    df = df_review_trends(pg, days=7)
    
    # Verify dataframe structure and contents
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    assert all(col in df.columns for col in ['date', 'count', 'avg_rating'])
    assert df['count'].sum() == 5  # Total reviews inserted
    assert 3 <= df['avg_rating'].mean() <= 5  # Average rating in expected range

def test_df_agent_volume(pg):
    """Test agent volume dataframe generation."""
    # Insert test data
    with pg() as conn:
        with conn.cursor() as cur:
            # Add reviews for different agents
            cur.execute("""
                INSERT INTO reviews (created_at, agent_id, conversation_id, rating)
                VALUES 
                    (now() - interval '2 days', 'agent1', 'conv1', 5),
                    (now() - interval '2 days', 'agent1', 'conv2', 4),
                    (now() - interval '1 day', 'agent2', 'conv3', 3),
                    (now() - interval '1 day', 'agent2', 'conv4', 5)
            """)
    
    # Test agent volume for last 3 days
    df = df_agent_volume(pg, days=3)
    
    # Verify dataframe structure and contents
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    assert all(col in df.columns for col in ['agent_id', 'review_count'])
    assert df['review_count'].sum() == 4  # Total reviews inserted
    assert len(df) == 2  # Two distinct agents

@pytest.mark.parametrize("days,expected_count", [
    (1, 0),  # No reviews in last day
    (3, 4),  # All reviews in last 3 days
    (7, 4),  # All reviews in last week
])
def test_df_review_trends_date_ranges(pg, days, expected_count):
    """Test review trends with different date ranges."""
    # Insert test data
    with pg() as conn:
        with conn.cursor() as cur:
            # Add reviews with specific dates
            cur.execute("""
                INSERT INTO reviews (created_at, agent_id, conversation_id, rating)
                VALUES 
                    (now() - interval '2 days', 'agent1', 'conv1', 5),
                    (now() - interval '2 days', 'agent1', 'conv2', 4),
                    (now() - interval '2 days', 'agent2', 'conv3', 3),
                    (now() - interval '2 days', 'agent2', 'conv4', 5)
            """)
    
    df = df_review_trends(pg, days=days)
    total_reviews = df['count'].sum()
    assert total_reviews == expected_count