"""One-time script to recompute quality_tier for all existing reviews.

Usage:
    cd backend
    python -m scripts.recompute_review_quality
"""

import asyncio

from sqlalchemy import func, select

from app.models.database import AsyncSessionLocal
from app.models.models import Developer, PRReview, PRReviewComment
from app.services.github_sync import classify_review_quality


async def recompute_all() -> None:
    async with AsyncSessionLocal() as db:
        reviews = list(
            (await db.execute(select(PRReview))).scalars().all()
        )
        print(f"Recomputing quality tiers for {len(reviews)} reviews...")

        updated = 0
        for review in reviews:
            # Resolve inline comment count for this reviewer on this review
            comment_count = 0
            if review.reviewer_id:
                dev_result = await db.execute(
                    select(Developer.github_username).where(
                        Developer.id == review.reviewer_id
                    )
                )
                reviewer_username = dev_result.scalar_one_or_none()
                if reviewer_username:
                    comment_count = (
                        await db.scalar(
                            select(func.count()).where(
                                PRReviewComment.pr_id == review.pr_id,
                                PRReviewComment.review_id == review.id,
                                PRReviewComment.author_github_username
                                == reviewer_username,
                            )
                        )
                        or 0
                    )

            new_tier = classify_review_quality(
                review.state,
                review.body_length,
                comment_count,
                body=review.body or "",
            )
            if new_tier != review.quality_tier:
                review.quality_tier = new_tier
                updated += 1

        await db.commit()
        print(f"Done. Updated {updated} of {len(reviews)} reviews.")


if __name__ == "__main__":
    asyncio.run(recompute_all())
