from rest_framework import serializers

from .models import NAME_LENGTH, Person


class PersonListSerializer(serializers.ModelSerializer):
    friends = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    emails = serializers.SerializerMethodField()

    class Meta:
        model = Person
        fields = (
            'id',
            'first_name',
            'middle_name',
            'last_name',
            'gender',
            'age',
            'nationality',
            'emails',
            'friends',
        )

    def get_emails(self, obj):
        return list(obj.emails.values_list('email', flat=True))


class PersonDetailSerializer(serializers.ModelSerializer):
    friends = PersonListSerializer(many=True, read_only=True)
    emails = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Person
        fields = (
            'id',
            'first_name',
            'middle_name',
            'last_name',
            'gender',
            'age',
            'nationality',
            'emails',
            'friends',
        )

    def get_emails(self, obj):
        return list(obj.emails.values_list('email', flat=True))


class PersonCreateUpdateSerializer(serializers.ModelSerializer):
    person_emails = serializers.ListField(
        child=serializers.EmailField(),
        required=False,
        write_only=True,
    )
    emails = serializers.SerializerMethodField(read_only=True)
    first_name = serializers.CharField(
        max_length=NAME_LENGTH,
        error_messages={
            'max_length': f'The name must not exceed {NAME_LENGTH}.'
        },
    )
    middle_name = serializers.CharField(
        max_length=NAME_LENGTH,
        required=False,
        allow_blank=True,
        allow_null=True,
        error_messages={
            'max_length': f'The patronymic must not exceed {NAME_LENGTH}.'
        },
    )
    last_name = serializers.CharField(
        max_length=NAME_LENGTH,
        error_messages={
            'max_length': f'Last name must not exceed {NAME_LENGTH}.'
        },
    )

    class Meta:
        model = Person
        fields = (
            'first_name',
            'middle_name',
            'last_name',
            'gender',
            'age',
            'nationality',
            'emails',
            'person_emails',
        )
        extra_kwargs = {
            'gender': {'read_only': True},
            'age': {'read_only': True},
            'nationality': {'read_only': True},
            'middle_name': {'required': False},
        }

    def get_emails(self, obj):
        return list(obj.emails.values_list('email', flat=True))


class AddRemoveFriendSerializer(serializers.Serializer):
    friend_id = serializers.IntegerField()
