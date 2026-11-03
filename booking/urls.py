from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("insights/", views.insights, name="insights"),
    path("staff/overview/", views.staff_overview, name="staff_overview"),
    path("staff/revenue/", views.staff_revenue, name="staff_revenue"),
    path("signup/", views.signup, name="signup"),
    path("login/", auth_views.LoginView.as_view(template_name="booking/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("trip/<int:trip_id>/", views.trip_detail, name="trip_detail"),
    path("trip/<int:trip_id>/hold/", views.create_hold, name="create_hold"),
    path("trip/<int:trip_id>/waitlist/", views.waitlist_join, name="waitlist_join"),
    path("waitlist/<int:entry_id>/leave/", views.waitlist_leave, name="waitlist_leave"),
    path("waitlist/<int:entry_id>/accept/", views.accept_offer, name="accept_offer"),
    path("bookings/", views.my_bookings, name="my_bookings"),
    path("bookings/<int:booking_id>/", views.booking_detail, name="booking_detail"),
    path("bookings/<int:booking_id>/confirm/", views.confirm, name="confirm"),
    path("bookings/<int:booking_id>/cancel/", views.cancel, name="cancel"),
    path("bookings/<int:booking_id>/review/", views.review_bus, name="review_bus"),
    path("support/", views.support, name="support"),
    path("account/", views.account_settings, name="account_settings"),
    path("account/update/", views.update_account_settings, name="update_account_settings"),
    path("account/history/", views.account_history, name="account_history"),
    path("account/password/", auth_views.PasswordChangeView.as_view(template_name="booking/change_password.html", success_url="/account/"), name="change_password"),
]
