from app.application.application_queue import (
    ApplicationQueue as BaseApplicationQueue,
)
from app.models.application_queue_item import (
    ApplicationQueueItem,
)
from app.models.application_recommendation import (
    ApplicationRecommendation,
)


class ApplicationQueue(BaseApplicationQueue):

    def build(
        self,
        recommendations: list[
            ApplicationRecommendation
        ],
    ) -> list[ApplicationQueueItem]:

        for recommendation in recommendations:

            if recommendation.recommendation == "REJECT":
                continue

            priority = self._priority(
                recommendation
            )

            self.add(
                recommendation,
                priority=priority,
            )

        return self.get_pending()

    @staticmethod
    def _priority(
        recommendation: ApplicationRecommendation,
    ) -> str:

        if (
            recommendation.recommendation == "APPLY"
            and recommendation.match_score >= 90
        ):
            return "HIGH"

        if recommendation.recommendation == "APPLY":
            return "NORMAL"

        return "LOW"

    @staticmethod
    def _sort_key(
        item: ApplicationQueueItem,
    ):

        priority_order = {
            "HIGH": 0,
            "NORMAL": 1,
            "LOW": 2,
        }

        return (
            priority_order.get(
                item.priority,
                99,
            ),
            -item.recommendation.match_score,
        )