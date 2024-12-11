from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, NotFound
from rest_framework.response import Response

from .models import Email, Person
from .serializers import (
    AddRemoveFriendSerializer,
    PersonCreateUpdateSerializer,
    PersonDetailSerializer,
    PersonListSerializer,
)


class PersonViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Person.objects.all().prefetch_related(
        Prefetch(
            'friends', queryset=Person.objects.prefetch_related('emails')
        ),
        'emails',
    )

    serializer_map = {
        'list': PersonListSerializer,
        'retrieve': PersonDetailSerializer,
        'create': PersonCreateUpdateSerializer,
        'update': PersonCreateUpdateSerializer,
        'partial_update': PersonCreateUpdateSerializer,
    }

    def get_serializer_class(self):
        return self.serializer_map.get(self.action, PersonDetailSerializer)

    @transaction.atomic
    def perform_create(self, serializer):
        emails = set(serializer.validated_data.pop('person_emails', []))
        existing_emails = Email.objects.filter(email__in=emails)
        if existing_emails.exists():
            existing = existing_emails.values_list('email', flat=True)
            raise APIException(
                f'Emails addresses already exist: {', '.join(existing)}',
                code=status.HTTP_409_CONFLICT,
            )
        person = serializer.save()
        self._create_emails(person, emails)

    @transaction.atomic
    def perform_update(self, serializer):
        emails = set(serializer.validated_data.pop('person_emails', None))
        person = serializer.save()
        if emails is not None:
            existing_emails = Email.objects.filter(email__in=emails).exclude(
                person=person
            )
            if existing_emails.exists():
                existing = existing_emails.values_list('email', flat=True)
                raise APIException(
                    f'Emails addresses already exist: {', '.join(existing)}',
                    code=status.HTTP_409_CONFLICT,
                )
            person.emails.all().delete()
            self._create_emails(person, emails)

    @staticmethod
    def _create_emails(person: Person, emails: set[str]):
        email_objs = [Email(person=person, email=email) for email in emails]
        Email.objects.bulk_create(email_objs)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='last_name',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                required=True,
                description='Last name to search for',
            )
        ],
        responses={
            status.HTTP_200_OK: PersonDetailSerializer(many=True),
            status.HTTP_400_BAD_REQUEST: OpenApiTypes.OBJECT,
            status.HTTP_404_NOT_FOUND: OpenApiTypes.OBJECT,
        },
        description='Search for a person by last name',
    )
    @action(detail=False, methods=['get'], url_path='search')
    def search_by_last_name(self, request):
        last_name = request.query_params.get('last_name')
        if not last_name:
            raise APIException(
                'The last_name parameter is required',
                code=status.HTTP_400_BAD_REQUEST,
            )
        persons = self.get_queryset().filter(last_name__iexact=last_name)
        if not persons.exists():
            raise NotFound(
                'The person with the specified surname has not been found'
            )

        serializer = PersonListSerializer(persons, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        responses={
            200: PersonListSerializer(many=True),
        },
        description='Getting a list of the users friends',
    )
    @action(detail=True, methods=['get'], url_path='friends')
    def get_friends(self, request, pk=None):
        person = self.get_object()
        friends = person.friends.all()
        serializer = PersonListSerializer(
            friends, many=True, context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=AddRemoveFriendSerializer,
        responses={
            status.HTTP_200_OK: PersonDetailSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiTypes.OBJECT,
            status.HTTP_404_NOT_FOUND: OpenApiTypes.OBJECT,
        },
        description='Adding a friend to a user',
    )
    @action(detail=True, methods=['post'], url_path='add-friend')
    def add_friend(self, request, pk=None):
        person = self.get_object()
        serializer = AddRemoveFriendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        friend_id = serializer.validated_data.get('friend_id')
        friend = get_object_or_404(Person, pk=friend_id)

        if person.friends.filter(pk=friend_id).exists():
            raise APIException(
                'This person is already a friend',
                code=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            person.friends.add(friend)
            friend.friends.add(person)

        serializer = PersonDetailSerializer(
            person, context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        request=AddRemoveFriendSerializer,
        responses={
            status.HTTP_200_OK: PersonDetailSerializer,
            status.HTTP_400_BAD_REQUEST: OpenApiTypes.OBJECT,
            status.HTTP_404_NOT_FOUND: OpenApiTypes.OBJECT,
        },
        description='Deleting a friend from a user',
    )
    @action(detail=True, methods=['post'], url_path='remove-friend')
    def remove_friend(self, request, pk=None):
        person = self.get_object()
        serializer = AddRemoveFriendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        friend_id = serializer.validated_data.get('friend_id')
        friend = get_object_or_404(Person, pk=friend_id)

        if not person.friends.filter(pk=friend_id).exists():
            raise APIException(
                'This person is not a friend', code=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            person.friends.remove(friend)
            friend.friends.remove(person)

        serializer = PersonDetailSerializer(
            person, context={'request': request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)
