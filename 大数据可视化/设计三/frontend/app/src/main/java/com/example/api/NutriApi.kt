package com.example.api

import com.example.api.dto.*
import okhttp3.MultipartBody
import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.*

interface NutriApi {

    // ── Health ──
    @GET("health")
    suspend fun health(): Response<Map<String, String>>

    // ── Meals ──
    @GET("meals")
    suspend fun getMeals(
        @Query("date") date: String? = null,
        @Query("start") start: String? = null,
        @Query("end") end: String? = null,
    ): Response<MealListResponseDto>

    @POST("meals")
    suspend fun createMeal(@Body body: CreateMealRequestDto): Response<MealDetailDto>

    @GET("meals/search")
    suspend fun searchMeals(
        @Query("q") query: String? = null,
        @Query("limit") limit: Int = 20,
    ): Response<MealListResponseDto>

    @GET("meals/{mealId}")
    suspend fun getMeal(@Path("mealId") mealId: String): Response<MealDetailDto>

    @PATCH("meals/{mealId}")
    suspend fun updateMeal(
        @Path("mealId") mealId: String,
        @Body body: Map<String, @JvmSuppressWildcards Any>,
    ): Response<MealDetailDto>

    @DELETE("meals/{mealId}")
    suspend fun deleteMeal(@Path("mealId") mealId: String): Response<Unit>

    @POST("meals/{mealId}/duplicate")
    suspend fun duplicateMeal(
        @Path("mealId") mealId: String,
        @Body body: DuplicateRequestDto,
    ): Response<MealDetailDto>

    @POST("meals/{mealId}/items")
    suspend fun addMealItem(
        @Path("mealId") mealId: String,
        @Body body: CreateMealItemDto,
    ): Response<MealDetailDto>

    @PATCH("meals/item/{itemId}")
    suspend fun updateMealItem(
        @Path("itemId") itemId: String,
        @Body body: Map<String, @JvmSuppressWildcards Any>,
    ): Response<MealDetailDto>

    @DELETE("meals/item/{itemId}")
    suspend fun deleteMealItem(@Path("itemId") itemId: String): Response<MealDetailDto>

    // ── Summary ──
    @GET("summary/day")
    suspend fun getDaySummary(@Query("date") date: String): Response<DaySummaryDto>

    // ── Analytics ──
    @GET("analytics/week")
    suspend fun getWeekAnalytics(
        @Query("start") start: String,
        @Query("end") end: String,
        @Query("metric") metric: String = "calories",
    ): Response<WeekAnalyticsDto>

    // ── Media ──
    @Multipart
    @POST("media/images")
    suspend fun uploadImage(
        @Part file: MultipartBody.Part,
        @Part("source") source: okhttp3.RequestBody,
    ): Response<MediaUploadResponseDto>

    // ── User ──
    @GET("users/me")
    suspend fun getCurrentUser(): Response<UserDto>

    @GET("users/me/targets")
    suspend fun getNutritionTargets(): Response<NutritionTargetsDto>
}
