package com.example.api.dto

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class UserDto(
    @Json(name = "id") val id: String,
    @Json(name = "displayName") val displayName: String,
    @Json(name = "avatarUrl") val avatarUrl: String?,
    @Json(name = "isTestUser") val isTestUser: Boolean,
)

@JsonClass(generateAdapter = true)
data class UserProfileDto(
    @Json(name = "nickname") val nickname: String,
    @Json(name = "gender") val gender: String,
    @Json(name = "age") val age: Int,
    @Json(name = "heightCm") val heightCm: Double,
    @Json(name = "weightKg") val weightKg: Double,
    @Json(name = "bodyFatRate") val bodyFatRate: Double?,
    @Json(name = "activityLevel") val activityLevel: String,
    @Json(name = "healthGoal") val healthGoal: String,
)

@JsonClass(generateAdapter = true)
data class NutritionTargetsDto(
    @Json(name = "bmr") val bmr: Int,
    @Json(name = "tdee") val tdee: Int,
    @Json(name = "targetCalories") val targetCalories: Int,
    @Json(name = "protein") val protein: Int,
    @Json(name = "carbs") val carbs: Int,
    @Json(name = "fat") val fat: Int,
)
