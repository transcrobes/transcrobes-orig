# -*- coding: utf-8 -*-

from registration.forms import (
    RegistrationFormTermsOfService,
    RegistrationFormUniqueEmail,
    RegistrationFormUsernameLowercase,
)


class RestrictiveRegistrationForm(
    RegistrationFormTermsOfService, RegistrationFormUniqueEmail, RegistrationFormUsernameLowercase
):
    pass
