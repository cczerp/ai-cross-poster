"""
Knowledge Distillation - Baby Bird Learning System
==================================================
Teacher-Student learning where Claude (teacher) trains an open-source
vision LLM (student) to handle collectible analysis.

Phase 1: Data Collection (NOW)
- Save every Claude analysis as training data
- Baby bird watches and learns

Phase 2: Training (Later, when you have 1000-5000 samples)
- Fine-tune LLaVA/Mistral-Vision on Claude's responses
- Student learns to mimic teacher

Phase 3: Production (When student is 80%+ accurate)
- Router decides: simple items → student (cheap)
-                  complex items → Claude (accurate)
- 100x cost reduction for common items
"""

import os
from typing import Dict, Any, Optional, List
from pathlib import Path


class CollectibleRouter:
    """
    Smart router that decides: Should we use student or teacher?

    Decision factors:
    - Estimated item value (high value = use Claude)
    - Collectible type (common = student, rare = Claude)
    - Student confidence (low confidence = escalate to Claude)
    - Training progress (not enough data yet = always Claude)
    """

    def __init__(self, db=None):
        self.db = db
        self.student_ready = False  # Baby bird hasn't hatched yet!
        self.min_training_samples = int(os.getenv("MIN_TRAINING_SAMPLES", "1000"))

    def check_student_readiness(self) -> bool:
        """Check if student model has enough training data"""
        if not self.db:
            return False

        sample_count = self.db.count_training_samples()
        print(f"🐣 Baby bird status: {sample_count}/{self.min_training_samples} training samples collected")

        if sample_count >= self.min_training_samples:
            print("🐦 Baby bird is ready to start practicing!")
            return True
        else:
            remaining = self.min_training_samples - sample_count
            print(f"🥚 Still in the egg. Need {remaining} more samples before training.")
            return False

    def should_use_student(
        self,
        basic_analysis: Dict[str, Any],
        estimated_value: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Decide if we should use student model or escalate to Claude.

        Returns:
            {
                "use_student": bool,
                "reason": str,
                "confidence": float
            }
        """
        # Check if student is even trained yet
        if not self.student_ready:
            self.student_ready = self.check_student_readiness()

        if not self.student_ready:
            return {
                "use_student": False,
                "reason": "Baby bird still learning (not enough training data)",
                "confidence": 0.0
            }

        # TODO: Once student model is trained, add real decision logic here
        # For now, always use Claude (student model doesn't exist yet)

        # Example future logic:
        # - If value > $100: use Claude
        # - If rare collectible: use Claude
        # - If common item student has seen before: use student
        # - If student confidence < 0.7: escalate to Claude

        return {
            "use_student": False,
            "reason": "Student model not deployed yet (still in training phase)",
            "confidence": 0.0
        }


class TrainingDataCollector:
    """
    Collects training data every time Claude analyzes a collectible.

    Baby bird watches Claude work and learns from every analysis.
    """

    def __init__(self, db=None):
        self.db = db

    def collect_sample(
        self,
        photo_paths: List[str],
        gemini_analysis: Dict[str, Any],
        claude_analysis: Dict[str, Any],
        user_id: Optional[int] = None,
        listing_id: Optional[int] = None,
        collectible_id: Optional[int] = None
    ):
        """
        Save a training sample when Claude analyzes something.

        Args:
            photo_paths: Paths to the collectible photos
            gemini_analysis: Gemini's basic analysis (what student will see)
            claude_analysis: Claude's deep analysis (what student should output)
            user_id, listing_id, collectible_id: For tracking
        """
        if not self.db:
            print("⚠️  No database - can't collect training data")
            return

        try:
            sample_id = self.db.save_training_sample(
                photo_paths=photo_paths,
                input_data=gemini_analysis,
                teacher_output=claude_analysis,
                user_id=user_id,
                listing_id=listing_id,
                collectible_id=collectible_id,
                used_teacher=True
            )

            # Check progress
            total_samples = self.db.count_training_samples()
            print(f"📊 Training sample #{sample_id} collected! Total: {total_samples}")

            # Milestone celebrations!
            if total_samples == 100:
                print("🎉 100 samples! Baby bird is watching closely...")
            elif total_samples == 500:
                print("🎊 500 samples! Baby bird is learning fast...")
            elif total_samples == 1000:
                print("🚀 1000 samples! Baby bird is ready to start practicing!")
                print("   Run: python scripts/train_student_model.py")

            return sample_id

        except Exception as e:
            print(f"❌ Failed to collect training sample: {e}")
            return None

    def export_training_data(self, output_path: str = "./data/training_dataset.jsonl"):
        """
        Export all training data for model fine-tuning.

        Use this when you're ready to train the student model.
        """
        if not self.db:
            print("⚠️  No database - can't export")
            return

        sample_count = self.db.export_training_dataset(output_path, format="jsonl")

        print(f"""
        ✅ Exported {sample_count} training samples!

        Next steps:
        1. Review the data: cat {output_path}
        2. Run training script: python scripts/train_student_model.py
        3. Model will be saved to: ./models/student_collectible_analyzer/

        After training, update STUDENT_MODEL_PATH in .env
        """)

        return sample_count


def get_baby_bird_status(db) -> Dict[str, Any]:
    """
    Get current status of baby bird training.

    Shows:
    - How many samples collected
    - How close to being ready to train
    - Estimated cost savings once deployed
    """
    if not db:
        return {"error": "No database connection"}

    total_samples = db.count_training_samples()
    min_needed = int(os.getenv("MIN_TRAINING_SAMPLES", "1000"))
    ready = total_samples >= min_needed

    # Calculate potential cost savings
    # Assume: Claude = $0.10 per analysis, Student = $0.001 per analysis
    # If 80% of analyses can use student after training
    potential_savings = total_samples * 0.10 * 0.8 * 0.999  # 99.9% savings on 80% of requests

    return {
        "samples_collected": total_samples,
        "samples_needed": min_needed,
        "progress_percent": min(100, (total_samples / min_needed) * 100),
        "ready_to_train": ready,
        "estimated_savings": f"${potential_savings:.2f}",
        "status": "🥚 In egg" if total_samples < 100 else
                 "🐣 Hatching soon" if total_samples < min_needed else
                 "🐦 Ready to fly!"
    }
