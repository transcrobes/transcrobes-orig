import * as Survey from "survey-react";
import "survey-react/survey.css";

import React from "react";
import ReactDOM from "react-dom";

const root = document.getElementById("root");
const surveyId = root.dataset.surveyId;
const userSurveyId = root.dataset.usersurveyId;
const username = root.dataset.user;

const surveyUrl = `/api/surveys/${surveyId}/`;
// const surveyUserUrl = `/api/usersurveys/?user__username=${username}&survey__id=${surveyId}`;

const get_headers = {
    credentials: "include",
    method:      "GET",
    headers: {
        "X-CSRFToken": csrftoken,
        "Accept": "application/json",
        "Content-Type": "application/json",
    },
};

//Define a callback methods on survey complete
function sendDataToServer(survey, options) {
    //Write survey results into database
    console.log("Survey results: " + JSON.stringify(survey.data));

    const amethod = userSurveyId ? 'PUT' : 'POST';
    const url = userSurveyId ? `/api/usersurveys/${userSurveyId}/` : "/api/usersurveys/";
    const data = {
        credentials: "include",
        method:      amethod,
        body: JSON.stringify({ survey: surveyUrl, data: survey.data }),
        headers: {
            "X-CSRFToken": csrftoken,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    };

    fetch(url, data)
        .then(response => {
            if (response.ok) {
                options.showDataSavingSuccess();
            } else {
                throw new Error(response.json());
            }
        }).catch((err) => {
            console.log(err);
            options.showDataSavingError();
        });
}

const model = new Survey.Model(surveyTemplate);
if (userSurvey) {
    model.data = userSurvey;
}
ReactDOM.render(
    <Survey.Survey model={model} onComplete={sendDataToServer}/>,
    root);
