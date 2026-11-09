from rest_framework import serializers

from referentiel.models import Article, Customer

from .forecast import MIN_NOTICE_DAYS, week_label
from .models import ForecastAdjustment, ForecastVersion, Promotion


def _user(user) -> str:
    return user.username if user else ""


class PromotionSerializer(serializers.ModelSerializer):
    customer_code = serializers.CharField(source="customer.code", read_only=True)
    article_code = serializers.CharField(source="article.code", read_only=True)
    article_name = serializers.CharField(source="article.name", read_only=True)
    first_week_label = serializers.SerializerMethodField()
    last_week_label = serializers.SerializerMethodField()
    notice_days = serializers.IntegerField(read_only=True)
    late_notice = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    cancelled_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Promotion
        fields = [
            "id", "customer", "customer_code", "article", "article_code", "article_name",
            "first_week", "first_week_label", "last_week", "last_week_label", "coefficient",
            "announced_on", "notice_days", "late_notice", "comment", "created_at",
            "created_by_name", "cancelled_at", "cancelled_by_name", "cancel_reason",
        ]  # fmt: skip

    def get_first_week_label(self, obj) -> str:
        return week_label(obj.first_week)

    def get_last_week_label(self, obj) -> str:
        return week_label(obj.last_week)

    def get_late_notice(self, obj) -> bool:
        return obj.notice_days < MIN_NOTICE_DAYS

    def get_created_by_name(self, obj) -> str:
        return _user(obj.created_by)

    def get_cancelled_by_name(self, obj) -> str:
        return _user(obj.cancelled_by)


class PromotionInputSerializer(serializers.Serializer):
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all())
    article = serializers.PrimaryKeyRelatedField(queryset=Article.objects.all())
    first_week = serializers.DateField()
    last_week = serializers.DateField()
    coefficient = serializers.DecimalField(max_digits=4, decimal_places=2)
    announced_on = serializers.DateField(required=False)
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class ReasonInputSerializer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=True)


class ForecastAdjustmentSerializer(serializers.ModelSerializer):
    customer_code = serializers.CharField(source="customer.code", read_only=True)
    article_code = serializers.CharField(source="article.code", read_only=True)
    week_label = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ForecastAdjustment
        fields = [
            "id", "customer", "customer_code", "article", "article_code", "week", "week_label",
            "quantity", "reason", "created_at", "created_by_name",
        ]  # fmt: skip

    def get_week_label(self, obj) -> str:
        return week_label(obj.week)

    def get_created_by_name(self, obj) -> str:
        return _user(obj.created_by)


class AdjustmentInputSerializer(serializers.Serializer):
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all())
    article = serializers.PrimaryKeyRelatedField(queryset=Article.objects.all())
    week = serializers.DateField()
    quantity = serializers.DecimalField(
        max_digits=12, decimal_places=3, allow_null=True, min_value=0
    )
    reason = serializers.CharField(allow_blank=True)


class ForecastVersionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.SerializerMethodField()
    source_label = serializers.CharField(source="get_source_display", read_only=True)
    first_week_label = serializers.SerializerMethodField()
    line_count = serializers.IntegerField(read_only=True)
    total_quantity = serializers.DecimalField(
        max_digits=14, decimal_places=3, read_only=True, allow_null=True
    )

    class Meta:
        model = ForecastVersion
        fields = [
            "id", "number", "created_at", "created_by_name", "source", "source_label",
            "first_week", "first_week_label", "comment", "line_count", "total_quantity",
        ]  # fmt: skip

    def get_created_by_name(self, obj) -> str:
        return _user(obj.created_by)

    def get_first_week_label(self, obj) -> str:
        return week_label(obj.first_week)


class VersionInputSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default="")
