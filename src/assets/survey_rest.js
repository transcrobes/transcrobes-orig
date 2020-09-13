import * as Survey from "survey-react";
import "survey-react/survey.css";

import React from "react";
import ReactDOM from "react-dom";

const root = document.getElementById("root");
const surveyId = root.dataset.surveyId;
const username = root.dataset.username;
//const

const surveyUrl = `/data/api/surveys/${surveyId}/`;
const surveyUserUrl = `/data/api/usersurveys/?user__username=${username}&survey__id=${surveyId}`;

const cookies = document.cookie.split('; ').reduce((acc, c) => {const [key, val] = c.split('='); acc[key] = val; return acc;}, {});

const data = {
    credentials: "include",
    method:      "GET",
    headers: {
        "X-CSRFToken": cookies["csrftoken"],
        "Accept": "application/json",
        "Content-Type": "application/json",
    },
};

//Define a callback methods on survey complete
function sendDataToServer(survey, options) {
    //Write survey results into database
    console.log("Survey results: " + JSON.stringify(survey.data));
    const data = {
        credentials: "include",
        method:      "POST",
        body: JSON.stringify({ survey: surveyUrl, data: survey.data }),
        headers: {
            "X-CSRFToken": cookies["csrftoken"],
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    };

    fetch('/data/api/usersurveys/', data)
        .then(res => res.json())
        .then(data =>
            options.showDataSavingSuccess()
        ).catch((err) => {
            console.log(err);
            options.showDataSavingError();
        });
}

Promise.all([
    fetch(surveyUrl, data).then(resp => resp.json()),
    fetch(surveyUserUrl, data).then(resp => resp.json())]).
    then((values) => {
        console.log(values);

        const model = new Survey.Model(values[0].survey_json);
        if (values[1].length) {
            model.data = values[1][0].data;
        }
        ReactDOM.render(
            <Survey.Survey model={model} onComplete={sendDataToServer}/>,
            root)
    });
