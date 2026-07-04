package com.example.api.dto

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class DayItemDto(
    @Json(name = "date") val date: String,
    @Json(name = "dateString") val dateString: String,
    @Json(name = "dayLabel") val dayLabel: String,
    @Json(name = "calories") val calories: Int = 0,
    @Json(name = "protein") val protein: Int = 0,
    @Json(name = "carbs") val carbs: Int = 0,
    @Json(name = "fat") val fat: Int = 0,
    @Json(name = "metricValue") val metricValue: Int = 0,
    @Json(name = "fatPercent") val fatPercent: Int = 0,
    @Json(name = "carbsPercent") val carbsPercent: Int = 0,
    @Json(name = "proteinPercent") val proteinPercent: Int = 0,
)

@JsonClass(generateAdapter = true)
data class WeeklyAverageDto(
    @Json(name = "fatPercent") val fatPercent: Int = 0,
    @Json(name = "carbsPercent") val carbsPercent: Int = 0,
    @Json(name = "proteinPercent") val proteinPercent: Int = 0,
)

@JsonClass(generateAdapter = true)
data class WeekAnalyticsDto(
    @Json(name = "dateRangeLabel") val dateRangeLabel: String,
    @Json(name = "metric") val metric: String,
    @Json(name = "metricLabel") val metricLabel: String,
    @Json(name = "metricUnit") val metricUnit: String,
    @Json(name = "recordedDays") val recordedDays: Int = 0,
    @Json(name = "averageValue") val averageValue: Int = 0,
    @Json(name = "targetValue") val targetValue: Int = 0,
    @Json(name = "days") val days: List<DayItemDto> = emptyList(),
    @Json(name = "weeklyAverage") val weeklyAverage: WeeklyAverageDto = WeeklyAverageDto(),
)
