import tempfile
import os

from PIL import Image
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

from cinema.models import Movie, MovieSession, CinemaHall, Genre, Actor
from cinema.views import MovieViewSet

MOVIE_URL = reverse("cinema:movie-list")
MOVIE_SESSION_URL = reverse("cinema:moviesession-list")


def sample_movie(**params):
    defaults = {
        "title": "Sample movie",
        "description": "Sample description",
        "duration": 90,
    }
    defaults.update(params)

    return Movie.objects.create(**defaults)


def sample_genre(**params):
    defaults = {
        "name": "Drama",
    }
    defaults.update(params)

    return Genre.objects.create(**defaults)


def sample_actor(**params):
    defaults = {"first_name": "George", "last_name": "Clooney"}
    defaults.update(params)

    return Actor.objects.create(**defaults)


def sample_movie_session(**params):
    cinema_hall = CinemaHall.objects.create(
        name="Blue", rows=20, seats_in_row=20
    )

    defaults = {
        "show_time": "2022-06-02 14:00:00",
        "movie": None,
        "cinema_hall": cinema_hall,
    }
    defaults.update(params)

    return MovieSession.objects.create(**defaults)


def image_upload_url(movie_id):
    """Return URL for recipe image upload"""
    return reverse("cinema:movie-upload-image", args=[movie_id])


def detail_url(movie_id):
    return reverse("cinema:movie-detail", args=[movie_id])


class MovieImageUploadTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_superuser(
            "admin@myproject.com", "password"
        )
        self.client.force_authenticate(self.user)
        self.movie = sample_movie()
        self.genre = sample_genre()
        self.actor = sample_actor()
        self.movie_session = sample_movie_session(movie=self.movie)

    def tearDown(self):
        self.movie.image.delete()

    def test_upload_image_to_movie(self):
        """Test uploading an image to movie"""
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(url, {"image": ntf}, format="multipart")
        self.movie.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("image", res.data)
        self.assertTrue(os.path.exists(self.movie.image.path))

    def test_upload_image_bad_request(self):
        """Test uploading an invalid image"""
        url = image_upload_url(self.movie.id)
        res = self.client.post(url, {"image": "not image"}, format="multipart")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_image_to_movie_list(self):
        url = MOVIE_URL
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            res = self.client.post(
                url,
                {
                    "title": "Title",
                    "description": "Description",
                    "duration": 90,
                    "genres": [1],
                    "actors": [1],
                    "image": ntf,
                },
                format="multipart",
            )

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        movie = Movie.objects.get(title="Title")
        self.assertFalse(movie.image)

    def test_image_url_is_shown_on_movie_detail(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(detail_url(self.movie.id))

        self.assertIn("image", res.data)

    def test_image_url_is_shown_on_movie_list(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_URL)

        self.assertIn("image", res.data[0].keys())

    def test_image_url_is_shown_on_movie_session_detail(self):
        url = image_upload_url(self.movie.id)
        with tempfile.NamedTemporaryFile(suffix=".jpg") as ntf:
            img = Image.new("RGB", (10, 10))
            img.save(ntf, format="JPEG")
            ntf.seek(0)
            self.client.post(url, {"image": ntf}, format="multipart")
        res = self.client.get(MOVIE_SESSION_URL)

        self.assertIn("movie_image", res.data[0].keys())


class MovieViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        action = Genre.objects.create(name="Action")
        crime = Genre.objects.create(name="Crime")

        actor1 = Actor.objects.create(first_name="Leonardo", last_name="DiCaprio")
        actor2 = Actor.objects.create(first_name="Elliot", last_name="Page")

        self.movie1 = Movie.objects.create(title="Inception", description="test", duration="12")
        self.movie2 = Movie.objects.create(title="Looper", description="test", duration="123")

        self.movie1.genres.set([action, crime])
        self.movie1.actors.set([actor1])

        self.movie2.genres.set([action])
        self.movie2.actors.set([actor2])

        self.user = get_user_model().objects.create_user(
            email="admin@admin.com",
            password="admin1111",
            is_staff=True
        )
        self.client.force_authenticate(self.user)

    def test_params_to_int(self):
        res = MovieViewSet._params_to_ints("1,2")
        self.assertEqual(res, [1, 2])

    def test_filter_movies_by_title(self):
        res = self.client.get("/api/cinema/movies/", {"title": "Inc"})

        self.assertEqual(res.data[0]["title"], "Inception")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_filter_movies_by_genres_ids(self):
        res = self.client.get("/api/cinema/movies/", {"genres": "2"})

        self.assertEqual(res.data[0]["title"], "Inception")

    def test_filter_movies_by_actors_ids(self):
        res = self.client.get("/api/cinema/movies/", {"actors": "2"})

        self.assertEqual(res.data[0]["title"], "Looper")


class PublicMovieViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.movie = Movie.objects.create(title="Movie", description="test", duration=12)

    def test_auth_required_movies(self):
        res = self.client.get("/api/cinema/movies/")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_required_creat_movie(self):
        url = reverse("cinema:movie-list")
        payload = {
            "title": "Movie",
            "description": "test",
            "duration": "12"
        }
        res = self.client.post(url, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_auth_required_upload_image(self):
        url = reverse("cinema:movie-upload-image", args=[self.movie.id])

        payload = {
            "image": "image.png"
        }
        res = self.client.post(url, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class UserMovieViewSetTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.movie = Movie.objects.create(title="Movie", description="test", duration=12)

        self.user = get_user_model().objects.create_user(
            email="admin@admin.com",
            password="admin1111",
            is_staff=False
        )
        self.client.force_authenticate(self.user)

    def test_is_staff_required_upload_image(self):
        url = reverse("cinema:movie-upload-image", args=[self.movie.id])

        payload = {
            "image": "image.png"
        }
        res = self.client.post(url, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
