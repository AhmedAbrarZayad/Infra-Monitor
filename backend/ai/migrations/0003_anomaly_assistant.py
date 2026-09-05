# Generated manually for the anomaly-focused Gemini assistant.

import uuid

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0011_allow_multiple_owned_organizations"),
        ("ai", "0002_aianalysis_incident_id_ailogfinding_log_id_and_more"),
        ("ml_model", "0004_anomalydetection_model_version_and_constraint"),
    ]

    operations = [
        migrations.AddField(
            model_name="assistantconversation",
            name="anomaly",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="assistant_conversations",
                to="ml_model.anomalydetection",
            ),
        ),
        migrations.AddField(
            model_name="assistantconversation",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="assistant_conversations",
                to="accounts.organization",
            ),
        ),
        migrations.AlterField(
            model_name="assistantconversation",
            name="conversation_id",
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name="assistantconversation",
            name="title",
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name="assistantconversation",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="assistantconversation",
            name="user_id",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="assistant_conversations",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterModelOptions(
            name="assistantconversation",
            options={"ordering": ["-updated_at", "conversation_id"]},
        ),
        migrations.AddConstraint(
            model_name="assistantconversation",
            constraint=models.UniqueConstraint(
                condition=Q(("anomaly__isnull", False)),
                fields=("organization", "user_id", "anomaly"),
                name="unique_user_anomaly_conversation",
            ),
        ),
        migrations.AddField(
            model_name="assistantmessage",
            name="client_message_id",
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="assistantmessage",
            name="response_to_client_message_id",
            field=models.UUIDField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="assistantmessage",
            name="created_at",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name="assistantmessage",
            name="evidence",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name="assistantmessage",
            name="message",
            field=models.TextField(),
        ),
        migrations.AlterField(
            model_name="assistantmessage",
            name="message_id",
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name="assistantmessage",
            name="sender_type",
            field=models.CharField(
                choices=[("USER", "User"), ("ASSISTANT", "Assistant")], max_length=16
            ),
        ),
        migrations.AlterModelOptions(
            name="assistantmessage",
            options={"ordering": ["created_at", "message_id"]},
        ),
        migrations.AddConstraint(
            model_name="assistantmessage",
            constraint=models.UniqueConstraint(
                fields=("conversation_id", "client_message_id"),
                name="unique_conversation_client_message",
            ),
        ),
        migrations.AddConstraint(
            model_name="assistantmessage",
            constraint=models.UniqueConstraint(
                fields=("conversation_id", "response_to_client_message_id"),
                name="unique_conversation_assistant_response",
            ),
        ),
        migrations.CreateModel(
            name="AssistantWebSocketTicket",
            fields=[
                (
                    "ticket_id",
                    models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
                ),
                ("token_hash", models.CharField(max_length=64, unique=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("used_at", models.DateTimeField(blank=True, null=True)),
                (
                    "conversation",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="ai.assistantconversation",
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="accounts.organization",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
