"""
Cloud Function to process voice transcripts
Triggered by Pub/Sub message, analyzes with Deepgram, updates BigQuery
"""
import base64
import json
import os
from datetime import datetime
from google.cloud import storage, bigquery
from deepgram import DeepgramClient
import functions_framework

# Initialize clients
storage_client = storage.Client()
bigquery_client = bigquery.Client()
deepgram_client = DeepgramClient(os.environ.get("DEEPGRAM_API_KEY"))

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "leafloaf-prod")
DATASET_ID = "leafloaf_analytics"
TABLE_ID = "voice_conversations"

@functions_framework.cloud_event
def process_transcript(cloud_event):
    """Process voice transcript from Pub/Sub trigger"""
    
    # Decode Pub/Sub message
    message = base64.b64decode(cloud_event.data["message"]["data"]).decode()
    data = json.loads(message)
    
    transcript_id = data["transcript_id"]
    gcs_path = data["gcs_path"]
    
    print(f"Processing transcript: {transcript_id}")
    
    try:
        # 1. Read transcript from Cloud Storage
        bucket_name = gcs_path.split("/")[2]
        blob_path = "/".join(gcs_path.split("/")[3:])
        
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        transcript_data = json.loads(blob.download_as_text())
        
        # 2. Analyze with Deepgram
        analysis_result = analyze_with_deepgram(
            transcript_data["transcript"]
        )
        
        # 3. Update BigQuery with analysis results
        update_bigquery(transcript_id, analysis_result)
        
        # 4. Optionally, store in Firestore for real-time access
        # update_firestore(transcript_data["user_id"], analysis_result)
        
        print(f"Successfully processed transcript: {transcript_id}")
        
    except Exception as e:
        print(f"Error processing transcript {transcript_id}: {e}")
        # Could implement retry logic or dead letter queue here
        raise


def analyze_with_deepgram(text: str) -> dict:
    """Analyze text using Deepgram's API"""
    try:
        # Use Deepgram's analyze API
        response = deepgram_client.analyze.v("1").analyze_text(
            {"text": text},
            {
                "language": "en",
                "sentiment": True,
                "intents": True,
                "topics": True,
                "entities": True,
                "summarize": True
            }
        )
        
        results = response.results
        
        # Extract analysis
        analysis = {
            "sentiment": None,
            "sentiment_score": 0.0,
            "intent": None,
            "intent_confidence": 0.0,
            "topics": [],
            "entities": [],
            "summary": ""
        }
        
        if results.sentiment and results.sentiment.segments:
            analysis["sentiment"] = results.sentiment.segments[0].sentiment
            analysis["sentiment_score"] = results.sentiment.segments[0].confidence
        
        if results.intents and results.intents.segments:
            intents = results.intents.segments[0].intents
            if intents:
                analysis["intent"] = intents[0].intent
                analysis["intent_confidence"] = intents[0].confidence
        
        if results.topics and results.topics.segments:
            analysis["topics"] = [
                t.topic for t in results.topics.segments[0].topics
            ]
        
        if results.entities and results.entities.entities:
            analysis["entities"] = [
                {
                    "entity": e.value,
                    "type": e.entity_type,
                    "confidence": e.confidence
                }
                for e in results.entities.entities
            ]
        
        if results.summary:
            analysis["summary"] = results.summary.short
        
        return analysis
        
    except Exception as e:
        print(f"Deepgram analysis error: {e}")
        return {
            "sentiment": "neutral",
            "sentiment_score": 0.5,
            "intent": "unknown",
            "intent_confidence": 0.0,
            "topics": [],
            "entities": [],
            "summary": ""
        }


def update_bigquery(transcript_id: str, analysis: dict):
    """Update BigQuery with analysis results"""
    table_id = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    
    # Prepare update query
    query = f"""
    UPDATE `{table_id}`
    SET 
        sentiment = @sentiment,
        sentiment_score = @sentiment_score,
        intent = @intent,
        intent_confidence = @intent_confidence,
        topics = @topics,
        entities = @entities,
        summary = @summary,
        processing_status = 'completed',
        processed_at = CURRENT_TIMESTAMP()
    WHERE transcript_id = @transcript_id
    """
    
    # Configure query parameters
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("transcript_id", "STRING", transcript_id),
            bigquery.ScalarQueryParameter("sentiment", "STRING", analysis["sentiment"]),
            bigquery.ScalarQueryParameter("sentiment_score", "FLOAT64", analysis["sentiment_score"]),
            bigquery.ScalarQueryParameter("intent", "STRING", analysis["intent"]),
            bigquery.ScalarQueryParameter("intent_confidence", "FLOAT64", analysis["intent_confidence"]),
            bigquery.ArrayQueryParameter("topics", "STRING", analysis["topics"]),
            bigquery.StructQueryParameter("entities", analysis["entities"]),
            bigquery.ScalarQueryParameter("summary", "STRING", analysis["summary"])
        ]
    )
    
    # Execute query
    query_job = bigquery_client.query(query, job_config=job_config)
    query_job.result()  # Wait for completion
    
    print(f"Updated BigQuery for transcript: {transcript_id}")