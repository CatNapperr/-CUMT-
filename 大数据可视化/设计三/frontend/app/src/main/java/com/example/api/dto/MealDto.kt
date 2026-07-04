package com.example.api.dto

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class AlternativeDto(
    @Json(name = "id") val id: String,
    @Json(name = "name") val name: String,
    @Json(name = "calories") val calories: Int?,
    @Json(name = "weightString") val weightString: String?,
)

@JsonClass(generateAdapter = true)
data class MealItemDto(
    @Json(name = "id") val id: String,
    @Json(name = "name") val name: String,
    @Json(name = "calories") val calories: Int,
    @Json(name = "protein") val protein: Int,
    @Json(name = "carbs") val carbs: Int,
    @Json(name = "fat") val fat: Int,
    @Json(name = "weightGrams") val weightGrams: Int?,
    @Json(name = "weightString") val weightString: String,
    @Json(name = "alternatives") val alternatives: List<AlternativeDto> = emptyList(),
)

@JsonClass(generateAdapter = true)
data class MealListItemDto(
    @Json(name = "id") val id: String,
    @Json(name = "title") val title: String,
    @Json(name = "mealType") val mealType: String,
    @Json(name = "mealTypeLabel") val mealTypeLabel: String,
    @Json(name = "mealDate") val mealDate: String,
    @Json(name = "dateString") val dateString: String,
    @Json(name = "timeString") val timeString: String,
    @Json(name = "calories") val calories: Int,
    @Json(name = "protein") val protein: Int,
    @Json(name = "carbs") val carbs: Int,
    @Json(name = "fat") val fat: Int,
    @Json(name = "imageUrl") val imageUrl: String?,
)

@JsonClass(generateAdapter = true)
data class MealDetailDto(
    @Json(name = "id") val id: String,
    @Json(name = "title") val title: String,
    @Json(name = "mealType") val mealType: String,
    @Json(name = "mealTypeLabel") val mealTypeLabel: String,
    @Json(name = "mealDate") val mealDate: String,
    @Json(name = "dateString") val dateString: String,
    @Json(name = "timeString") val timeString: String,
    @Json(name = "calories") val calories: Int,
    @Json(name = "protein") val protein: Int,
    @Json(name = "carbs") val carbs: Int,
    @Json(name = "fat") val fat: Int,
    @Json(name = "notes") val notes: String,
    @Json(name = "imageId") val imageId: String?,
    @Json(name = "imageUrl") val imageUrl: String?,
    @Json(name = "multiplier") val multiplier: Double,
    @Json(name = "isCollected") val isCollected: Boolean,
    @Json(name = "isLiked") val isLiked: Boolean?,
    @Json(name = "healthScore") val healthScore: String?,
    @Json(name = "healthMessage") val healthMessage: String?,
    @Json(name = "source") val source: String,
    @Json(name = "items") val items: List<MealItemDto> = emptyList(),
)

@JsonClass(generateAdapter = true)
data class MealListResponseDto(
    @Json(name = "items") val items: List<MealListItemDto>,
)

@JsonClass(generateAdapter = true)
data class CreateMealRequestDto(
    @Json(name = "title") val title: String,
    @Json(name = "mealType") val mealType: String,
    @Json(name = "mealDate") val mealDate: String,
    @Json(name = "timeString") val timeString: String,
    @Json(name = "notes") val notes: String = "",
    @Json(name = "imageId") val imageId: String? = null,
    @Json(name = "imageUrl") val imageUrl: String? = null,
    @Json(name = "multiplier") val multiplier: Double = 1.0,
    @Json(name = "isCollected") val isCollected: Boolean = false,
    @Json(name = "isLiked") val isLiked: Boolean? = null,
    @Json(name = "healthScore") val healthScore: String? = null,
    @Json(name = "healthMessage") val healthMessage: String? = null,
    @Json(name = "source") val source: String,
    @Json(name = "items") val items: List<CreateMealItemDto>,
)

@JsonClass(generateAdapter = true)
data class CreateMealItemDto(
    @Json(name = "name") val name: String,
    @Json(name = "calories") val calories: Int = 0,
    @Json(name = "protein") val protein: Int = 0,
    @Json(name = "carbs") val carbs: Int = 0,
    @Json(name = "fat") val fat: Int = 0,
    @Json(name = "weightGrams") val weightGrams: Int? = null,
    @Json(name = "weightString") val weightString: String = "",
)

@JsonClass(generateAdapter = true)
data class DuplicateRequestDto(
    @Json(name = "mealDate") val mealDate: String,
    @Json(name = "timeString") val timeString: String,
    @Json(name = "source") val source: String = "search_history",
)
