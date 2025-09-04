from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
import time

try:
    from ..llm import rewrite_insight_llm, OPENAI_AVAILABLE
    LLM_AVAILABLE = OPENAI_AVAILABLE
except Exception:
    LLM_AVAILABLE = False

    def rewrite_insight_llm(*args, **kwargs):
        raise RuntimeError("LLM not available")


class ThreadedLLMService:
    """Service for handling LLM operations with threading for better performance."""

    def __init__(self, max_workers: int = 5, timeout: float = 60.0, batch_size: int = 10):
        self.max_workers = max_workers
        self.timeout = timeout
        self.batch_size = batch_size

    def rewrite_insights_batch(self, insights: List[Dict], tone: str = "friendly") -> List[Dict]:
        """
        Rewrite multiple insights using threading for parallel processing.
        Processes in smaller batches to avoid timeouts.
        Returns the insights with LLM rewrites applied if successful.
        """
        if not LLM_AVAILABLE or not insights:
            return insights

        print(
            f"Starting to rewrite {len(insights)} insights in batches of {self.batch_size}...")

        def rewrite_single_insight(insight: Dict) -> Dict:
            """Rewrite a single insight and return the updated insight."""
            try:
                original_title = insight.get("title", "")
                original_body = insight.get("body", "")
                data_json = insight.get("data_json", "")

                new_text = rewrite_insight_llm(
                    original_title, original_body, data_json, tone)

                # Update the insight with rewritten content
                insight_copy = insight.copy()
                insight_copy["rewritten_title"] = new_text.get(
                    "title", original_title)
                insight_copy["rewritten_body"] = new_text.get(
                    "body", original_body)
                insight_copy["rewritten_at"] = time.strftime(
                    "%Y-%m-%d %H:%M:%S")

                return insight_copy
            except Exception as e:
                # If rewriting fails, return original insight
                print(
                    f"Failed to rewrite insight {insight.get('id', 'unknown')}: {e}")
                return insight

        # Process insights in smaller batches to avoid timeouts
        all_rewritten = []

        for i in range(0, len(insights), self.batch_size):
            batch = insights[i:i + self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (
                len(insights) + self.batch_size - 1) // self.batch_size

            print(
                f"Processing batch {batch_num}/{total_batches} ({len(batch)} insights)...")

            batch_results = []

            # Use ThreadPoolExecutor for parallel processing of this batch
            with ThreadPoolExecutor(max_workers=min(self.max_workers, len(batch))) as executor:
                # Submit all rewrite tasks for this batch
                future_to_insight = {
                    executor.submit(rewrite_single_insight, insight): insight
                    for insight in batch
                }

                completed_count = 0

                # Collect results with timeout
                try:
                    for future in as_completed(future_to_insight, timeout=self.timeout):
                        try:
                            rewritten_insight = future.result()
                            batch_results.append(rewritten_insight)
                            completed_count += 1
                        except Exception as e:
                            # If a specific insight fails, use the original
                            original_insight = future_to_insight[future]
                            print(
                                f"Failed to process insight {original_insight.get('id', 'unknown')}: {e}")
                            batch_results.append(original_insight)
                            completed_count += 1

                except TimeoutError:
                    print(
                        f"Timeout in batch {batch_num}: {completed_count}/{len(batch)} insights completed")
                    # For any unfinished insights, use the original
                    for future, insight in future_to_insight.items():
                        if not future.done():
                            batch_results.append(insight)

            all_rewritten.extend(batch_results)
            print(
                f"Batch {batch_num} completed: {len(batch_results)} insights processed")

        # Ensure we maintain the original order
        insight_id_to_rewritten = {
            insight["id"]: insight for insight in all_rewritten}
        ordered_results = []
        for original_insight in insights:
            insight_id = original_insight["id"]
            if insight_id in insight_id_to_rewritten:
                ordered_results.append(insight_id_to_rewritten[insight_id])

        print(
            f"Completed rewriting: {len(ordered_results)} insights processed")
        return ordered_results

    def rewrite_single_insight_async(self, insight: Dict, tone: str = "friendly") -> Dict:
        """
        Rewrite a single insight asynchronously. This is useful for per-transaction insights.
        """
        if not LLM_AVAILABLE:
            return insight

        def background_rewrite():
            try:
                original_title = insight.get("title", "")
                original_body = insight.get("body", "")
                data_json = insight.get("data_json", "")

                new_text = rewrite_insight_llm(
                    original_title, original_body, data_json, tone)

                # Store the rewritten content (this would need database update in practice)
                print(
                    f"Background rewrite completed for insight {insight.get('id', 'unknown')}")
                return new_text
            except Exception as e:
                print(
                    f"Background rewrite failed for insight {insight.get('id', 'unknown')}: {e}")
                return None

        # Start background thread for rewriting
        thread = threading.Thread(target=background_rewrite, daemon=True)
        thread.start()

        # Return original insight immediately
        return insight


# Global instance with optimized settings
threaded_llm_service = ThreadedLLMService(
    max_workers=3, timeout=60.0, batch_size=8)
