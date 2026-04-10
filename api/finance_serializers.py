from rest_framework import serializers
from apps.orders.models import Expense
from django.contrib.auth import get_user_model

User = get_user_model()

class ExpenseSerializer(serializers.ModelSerializer):
    performed_by_name = serializers.ReadOnlyField(source='performed_by.get_full_name')
    performed_by_username = serializers.ReadOnlyField(source='performed_by.username')
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Expense
        fields = [
            'id', 'category', 'category_display', 'amount', 
            'date', 'note', 'performed_by', 'performed_by_name', 
            'performed_by_username', 'created_at'
        ]
        read_only_fields = ['performed_by', 'created_at']

    def create(self, validated_data):
        validated_data['performed_by'] = self.context['request'].user
        return super().create(validated_data)
