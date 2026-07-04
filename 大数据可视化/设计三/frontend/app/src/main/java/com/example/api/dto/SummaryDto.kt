package com.example.api.dto

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class DaySummaryDto(
    @Json(name = "date") val date: String,
    @Json(name = "dateString") val dateString: String,
    @Json(name = "targetCalories") val targetCalories: Int,
    @Json(name = "calories") val calories: Int,
    @Json(name = "remainingCalories") val remainingCalories: Int,
    @Json(name = "protein") val protein: Int,
    @Json(name = "proteinTarget") val proteinTarget: Int,
    @Json(name = "carbs") val carbs: Int,
    @Json(name = "carbsTarget") val carbsTarget: Int,
    @Json(name = "fat") val fat: Int,
    @Json(name = "fatTarget") val fatTarget: Int,
    @Json(name = "mealCount") val mealCount: Int,
)
