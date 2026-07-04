package com.example.ui.viewmodel

import android.app.Application
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.example.api.ApiClient
import com.example.api.dto.*
import com.example.data.*
import com.example.api.GeminiClient
import com.squareup.moshi.Moshi
import com.squareup.moshi.Types
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*

enum class MainTab {
    HOME, DIARY, ANALYSIS, PROFILE
}

class NutriViewModel(application: Application) : AndroidViewModel(application) {

    private val db = AppDatabase.getDatabase(application)
    private val repository = MealRepository(db.mealDao())
    private val api = ApiClient.api

    // ── Tab state ──
    private val _currentTab = MutableStateFlow(MainTab.HOME)
    val currentTab: StateFlow<MainTab> = _currentTab.asStateFlow()

    fun selectTab(tab: MainTab) { _currentTab.value = tab }

    // ── All cached meals from Room ──
    val loggedMeals: StateFlow<List<Meal>> = repository.allMeals
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    // ── API availability ──
    private val _apiAvailable = MutableStateFlow(false)
    val apiAvailable: StateFlow<Boolean> = _apiAvailable.asStateFlow()

    // ── Calendar state ──
    private val _selectedDateStr = MutableStateFlow("6月1日")
    val selectedDateStr: StateFlow<String> = _selectedDateStr.asStateFlow()

    private val _selectedDateIso = MutableStateFlow("2026-06-01")
    val selectedDateIso: StateFlow<String> = _selectedDateIso.asStateFlow()

    fun setSelectedDate(date: String) {
        _selectedDateStr.value = date
        // Derive ISO date from display date (simple mapping for MVP)
        _selectedDateIso.value = dateStringToIso(date)
        refreshDaySummary()
    }

    // ── Summary (from API) ──
    private val _daySummary = MutableStateFlow<DaySummaryDto?>(null)
    val daySummary: StateFlow<DaySummaryDto?> = _daySummary.asStateFlow()

    // ── Nutrition targets (from API) ──
    private val _nutritionTargets = MutableStateFlow(NutritionTargetsDto(
        bmr = 0, tdee = 0, targetCalories = 2391, protein = 90, carbs = 250, fat = 65
    ))
    val nutritionTargets: StateFlow<NutritionTargetsDto> = _nutritionTargets.asStateFlow()

    // ── Week analytics (from API) ──
    data class WeekQuery(val start: String, val end: String)
    private val _activeWeek = MutableStateFlow(WeekQuery("2026-05-25", "2026-05-31"))
    val activeWeek: StateFlow<WeekQuery> = _activeWeek.asStateFlow()

    private val _weekAnalytics = MutableStateFlow<WeekAnalyticsDto?>(null)
    val weekAnalytics: StateFlow<WeekAnalyticsDto?> = _weekAnalytics.asStateFlow()

    private val _selectedMetric = MutableStateFlow("calories")
    val selectedMetric: StateFlow<String> = _selectedMetric.asStateFlow()

    // ── AI input state ──
    private val _isAnalyzing = MutableStateFlow(false)
    val isAnalyzing: StateFlow<Boolean> = _isAnalyzing.asStateFlow()

    // ── Meal Details Overlay ──
    private val _showMealDetailsOverlay = MutableStateFlow(false)
    val showMealDetailsOverlay: StateFlow<Boolean> = _showMealDetailsOverlay.asStateFlow()

    private val _mealUnderReview = MutableStateFlow<Meal?>(null)
    val mealUnderReview: StateFlow<Meal?> = _mealUnderReview.asStateFlow()

    private val _reviewedItems = MutableStateFlow<List<FoodItem>>(emptyList())
    val reviewedItems: StateFlow<List<FoodItem>> = _reviewedItems.asStateFlow()

    private val _reviewedNotes = MutableStateFlow("")
    val reviewedNotes: StateFlow<String> = _reviewedNotes.asStateFlow()

    private val _portionScale = MutableStateFlow(1)
    val portionScale: StateFlow<Int> = _portionScale.asStateFlow()

    private val _reviewedIsCollected = MutableStateFlow(false)
    val reviewedIsCollected: StateFlow<Boolean> = _reviewedIsCollected.asStateFlow()

    private val _reviewedIsLiked = MutableStateFlow<Boolean?>(null)
    val reviewedIsLiked: StateFlow<Boolean?> = _reviewedIsLiked.asStateFlow()

    private val _deductActiveBurn = MutableStateFlow(false)
    val deductActiveBurn: StateFlow<Boolean> = _deductActiveBurn.asStateFlow()

    fun toggleActiveBurn() { _deductActiveBurn.value = !_deductActiveBurn.value }

    private val moshi = Moshi.Builder().addLast(KotlinJsonAdapterFactory()).build()
    private val type = Types.newParameterizedType(List::class.java, FoodItem::class.java)
    private val adapter = moshi.adapter<List<FoodItem>>(type)

    init {
        // Preseed with mock meals on first launch
        viewModelScope.launch {
            repository.allMeals.first().let { meals ->
                if (meals.isEmpty()) {
                    presetMockMeals()
                }
            }
        }
        // Check API availability and fetch data
        viewModelScope.launch {
            try {
                val healthResp = api.health()
                _apiAvailable.value = healthResp.isSuccessful
                if (healthResp.isSuccessful) {
                    refreshAll()
                }
            } catch (e: Exception) {
                Log.w("NutriViewModel", "Backend not available, using local data: ${e.message}")
                _apiAvailable.value = false
            }
        }
    }

    private suspend fun refreshAll() {
        try {
            val targetsResp = api.getNutritionTargets()
            if (targetsResp.isSuccessful) {
                targetsResp.body()?.let { _nutritionTargets.value = it }
            }
            refreshDaySummary()
            refreshWeekAnalytics()
            syncMealsFromApi()
        } catch (e: Exception) {
            Log.e("NutriViewModel", "Failed to refresh from API", e)
        }
    }

    private suspend fun syncMealsFromApi() {
        try {
            // Sync last 30 days of meals
            val cal = Calendar.getInstance()
            val endSdf = SimpleDateFormat("yyyy-MM-dd", Locale.US)
            val endDate = endSdf.format(cal.time)
            cal.add(Calendar.DAY_OF_YEAR, -30)
            val startDate = endSdf.format(cal.time)

            val resp = api.getMeals(start = startDate, end = endDate)
            if (resp.isSuccessful) {
                val mealList = resp.body()?.items ?: return
                for (dto in mealList) {
                    repository.insert(dtoToMeal(dto))
                }
            }
        } catch (e: Exception) {
            Log.w("NutriViewModel", "Failed to sync meals from API", e)
        }
    }

    fun refreshDaySummary() {
        viewModelScope.launch {
            try {
                val resp = api.getDaySummary(_selectedDateIso.value)
                if (resp.isSuccessful) {
                    resp.body()?.let { _daySummary.value = it }
                }
            } catch (e: Exception) {
                Log.w("NutriViewModel", "Failed to fetch day summary", e)
            }
        }
    }

    fun refreshWeekAnalytics() {
        viewModelScope.launch {
            try {
                val week = _activeWeek.value
                val resp = api.getWeekAnalytics(week.start, week.end, _selectedMetric.value)
                if (resp.isSuccessful) {
                    resp.body()?.let { _weekAnalytics.value = it }
                }
            } catch (e: Exception) {
                Log.w("NutriViewModel", "Failed to fetch week analytics", e)
            }
        }
    }

    fun setWeekRange(start: String, end: String) {
        _activeWeek.value = WeekQuery(start, end)
        refreshWeekAnalytics()
    }

    fun setAnalyticsMetric(metric: String) {
        _selectedMetric.value = metric
        refreshWeekAnalytics()
    }

    // ── Mock preset ──

    private suspend fun presetMockMeals() {
        val tofuItems = listOf(
            FoodItem("豆腐", 66, "1 份, 80克", listOf("丹贝", "印度芝士", "鸡蛋豆腐")),
            FoodItem("木耳", 8, "1 份, 30克", listOf("香菇", "口蘑")),
            FoodItem("酸辣汤底", 58, "1 杯, 240克", listOf("蛋花汤底", "味噌汤底"))
        )
        repository.insert(Meal(
            id = UUID.randomUUID().toString(), title = "豆腐木耳热汤", mealType = "晚餐",
            mealDate = "2026-05-29", dateString = "5月29日", timeString = "18:11",
            calories = 131, protein = 11, carbs = 12, fat = 5,
            notes = "很好喝的热汤，豆腐很嫩！",
            imageUrl = "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=500&auto=format&fit=crop&q=60",
            multiplier = 1.0, isCollected = true, isLiked = true,
            healthScore = "B", healthMessage = "整体营养均衡良好",
            itemsJson = adapter.toJson(tofuItems)
        ))
        val chickenItems = listOf(
            FoodItem("嫩煎烤鸡胸肉", 210, "1 份, 120克", listOf("白切鸡", "慢炖鸡胸肉")),
            FoodItem("白米饭", 185, "150克", listOf("红米饭", "燕麦大麦")),
            FoodItem("炒青菜(油菜)", 66, "1 份, 100克", listOf("清汤生菜", "蒸西兰花"))
        )
        repository.insert(Meal(
            id = UUID.randomUUID().toString(), title = "烤鸡, 白米饭, 炒青菜", mealType = "晚餐",
            mealDate = "2026-05-29", dateString = "5月29日", timeString = "17:58",
            calories = 461, protein = 40, carbs = 44, fat = 12,
            notes = "晚餐加餐！烤鸡肉很入味，高蛋白低脂餐。",
            imageUrl = "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=500&auto=format&fit=crop&q=60",
            multiplier = 1.0, isCollected = false, isLiked = true,
            healthScore = "A", healthMessage = "整体由于强营养吸收高蛋白",
            itemsJson = adapter.toJson(chickenItems)
        ))
        repository.insert(Meal(
            id = UUID.randomUUID().toString(), title = "香煎安格斯慢烤西冷牛排", mealType = "晚餐",
            mealDate = "2026-05-15", dateString = "5月15日", timeString = "19:00",
            calories = 480, protein = 38, carbs = 5, fat = 28,
            imageUrl = "https://images.unsplash.com/photo-1432139555190-58524dae6a55?w=500&auto=format&fit=crop&q=60",
            itemsJson = "[]", healthScore = "A", healthMessage = "高优质蛋白，红肉可适度补充"
        ))
        repository.insert(Meal(
            id = UUID.randomUUID().toString(), title = "精选牛油果大虾轻食沙拉", mealType = "午餐",
            mealDate = "2026-05-22", dateString = "5月22日", timeString = "12:00",
            calories = 340, protein = 24, carbs = 18, fat = 15,
            imageUrl = "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=500&auto=format&fit=crop&q=60",
            multiplier = 1.0, isCollected = true, isLiked = true,
            healthScore = "A", healthMessage = "极佳的减脂高蛋白选择", itemsJson = "[]"
        ))
        repository.insert(Meal(
            id = UUID.randomUUID().toString(), title = "精选牛油果大虾轻食沙拉", mealType = "午餐",
            mealDate = "2026-05-27", dateString = "5月27日", timeString = "12:30",
            calories = 340, protein = 24, carbs = 18, fat = 15,
            imageUrl = "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=500&auto=format&fit=crop&q=60",
            multiplier = 1.0, isCollected = true, isLiked = true,
            healthScore = "A", healthMessage = "极佳的减脂高蛋白选择", itemsJson = "[]"
        ))
        repository.insert(Meal(
            id = UUID.randomUUID().toString(), title = "全麦无糖高纤燕麦包", mealType = "早餐",
            mealDate = "2026-06-01", dateString = "6月1日", timeString = "08:30",
            calories = 195, protein = 8, carbs = 36, fat = 3,
            imageUrl = "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=500&auto=format&fit=crop&q=60",
            multiplier = 1.0, isCollected = true, isLiked = true,
            healthScore = "A", healthMessage = "优秀的早餐粗粮膳食纤维", itemsJson = "[]"
        ))
        repository.insert(Meal(
            id = UUID.randomUUID().toString(), title = "低卡烟熏三文鱼藜麦轻卡波奇饭", mealType = "晚餐",
            mealDate = "2026-06-04", dateString = "6月4日", timeString = "18:30",
            calories = 410, protein = 28, carbs = 42, fat = 14,
            imageUrl = "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=500&auto=format&fit=crop&q=60",
            multiplier = 1.0, isCollected = true, isLiked = true,
            healthScore = "A", healthMessage = "Omega-3不饱和脂肪酸极其丰富", itemsJson = "[]"
        ))
    }

    // ── AI Analysis ──

    fun analyzeAndReviewMeal(textDescription: String, customTime: String = "") {
        if (textDescription.trim().isEmpty()) return
        _isAnalyzing.value = true
        viewModelScope.launch {
            try {
                val calendar = Calendar.getInstance()
                val currentHour = calendar.get(Calendar.HOUR_OF_DAY)
                val inferredMealType = when {
                    currentHour < 10 -> "早餐"
                    currentHour < 15 -> "午餐"
                    else -> "晚餐"
                }
                val result = GeminiClient.analyzeMealText(textDescription)
                val sdfDate = SimpleDateFormat("M月d日", Locale.CHINESE)
                val currentFormattedDate = sdfDate.format(Date())
                val timeSdf = SimpleDateFormat("HH:mm", Locale.getDefault())
                val currentFormattedTime = if (customTime.isNotEmpty()) customTime else timeSdf.format(Date())

                val imageSelector = when {
                    result.title.contains("鸡") || result.title.contains("肉") -> "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=500&auto=format&fit=crop&q=60"
                    result.title.contains("汤") || result.title.contains("豆腐") -> "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=500&auto=format&fit=crop&q=60"
                    result.title.contains("鱼") || result.title.contains("海鲜") -> "https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=500&auto=format&fit=crop&q=60"
                    else -> "https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=500&auto=format&fit=crop&q=60"
                }

                val parsedMeal = Meal(
                    id = UUID.randomUUID().toString(),
                    title = result.title,
                    mealType = result.mealType.ifEmpty { inferredMealType },
                    mealDate = _selectedDateIso.value,
                    dateString = _selectedDateStr.value,
                    timeString = currentFormattedTime,
                    calories = result.calories,
                    protein = result.protein,
                    carbs = result.carbs,
                    fat = result.fat,
                    notes = "",
                    imageUrl = imageSelector,
                    multiplier = 1.0,
                    isCollected = false,
                    isLiked = null,
                    healthScore = result.healthScore,
                    healthMessage = result.healthMessage,
                    source = "ai_text",
                    itemsJson = adapter.toJson(result.items.map {
                        FoodItem(it.name, it.calories, it.weightString, it.alternatives)
                    })
                )
                openMealForReview(parsedMeal)
            } catch (e: Exception) {
                Log.e("NutriViewModel", "Error analyzing food prompt: ${e.message}")
            } finally {
                _isAnalyzing.value = false
            }
        }
    }

    // ── Review Sheet ──

    fun openMealForReview(meal: Meal) {
        _mealUnderReview.value = meal
        _reviewedNotes.value = meal.notes
        _portionScale.value = meal.multiplier.toInt().coerceAtLeast(1)
        _reviewedIsCollected.value = meal.isCollected
        _reviewedIsLiked.value = meal.isLiked
        _reviewedItems.value = try {
            adapter.fromJson(meal.itemsJson) ?: emptyList()
        } catch (e: Exception) { emptyList() }
        _showMealDetailsOverlay.value = true
    }

    fun updateReviewedNotes(notes: String) { _reviewedNotes.value = notes }
    fun changePortion(delta: Int) { _portionScale.value = (_portionScale.value + delta).coerceIn(1, 10) }
    fun toggleReviewedCollection() { _reviewedIsCollected.value = !_reviewedIsCollected.value }
    fun setReviewedLiked(liked: Boolean?) { _reviewedIsLiked.value = liked }

    fun addMissingFoodItem(name: String, calories: Int, weightDesc: String) {
        val currentItems = _reviewedItems.value.toMutableList()
        currentItems.add(FoodItem(name, calories, weightDesc, listOf("其他健康代餐", "高纤维平替")))
        _reviewedItems.value = currentItems
        _mealUnderReview.value?.let { currentMeal ->
            val additionalKcal = calories
            val additionalProtein = (calories * 0.08f).toInt().coerceAtLeast(1)
            val additionalCarbs = (calories * 0.10f).toInt().coerceAtLeast(1)
            val additionalFat = (calories * 0.04f).toInt().coerceAtLeast(1)
            _mealUnderReview.value = currentMeal.copy(
                calories = currentMeal.calories + additionalKcal,
                protein = currentMeal.protein + additionalProtein,
                carbs = currentMeal.carbs + additionalCarbs,
                fat = currentMeal.fat + additionalFat,
                itemsJson = adapter.toJson(currentItems)
            )
        }
    }

    fun saveReviewedMeal() {
        val rawMeal = _mealUnderReview.value ?: return
        val currentNotes = _reviewedNotes.value
        val currentScale = _portionScale.value.toDouble()
        val currentItemsList = _reviewedItems.value

        val scaledMeal = rawMeal.copy(
            calories = (rawMeal.calories * (currentScale / rawMeal.multiplier)).toInt(),
            protein = (rawMeal.protein * (currentScale / rawMeal.multiplier)).toInt(),
            carbs = (rawMeal.carbs * (currentScale / rawMeal.multiplier)).toInt(),
            fat = (rawMeal.fat * (currentScale / rawMeal.multiplier)).toInt(),
            multiplier = currentScale,
            notes = currentNotes,
            isCollected = _reviewedIsCollected.value,
            isLiked = _reviewedIsLiked.value,
            itemsJson = adapter.toJson(currentItemsList)
        )
        viewModelScope.launch {
            // Save locally
            repository.insert(scaledMeal)
            // Try to save to API
            if (_apiAvailable.value) {
                try {
                    api.createMeal(mealToCreateDto(scaledMeal))
                } catch (e: Exception) {
                    Log.w("NutriViewModel", "Failed to save meal to API", e)
                }
            }
            _showMealDetailsOverlay.value = false
            _mealUnderReview.value = null
            refreshDaySummary()
        }
    }

    fun cancelReview() {
        _showMealDetailsOverlay.value = false
        _mealUnderReview.value = null
    }

    fun deleteMeal(meal: Meal) {
        viewModelScope.launch {
            repository.deleteById(meal.id)
            if (_apiAvailable.value) {
                try { api.deleteMeal(meal.id) }
                catch (e: Exception) { Log.w("NutriViewModel", "Failed to delete meal from API", e) }
            }
            if (_mealUnderReview.value?.id == meal.id) {
                _showMealDetailsOverlay.value = false
                _mealUnderReview.value = null
            }
            refreshDaySummary()
        }
    }

    fun toggleMealCollectionInList(meal: Meal) {
        viewModelScope.launch {
            val updated = meal.copy(isCollected = !meal.isCollected)
            repository.insert(updated)
            if (_apiAvailable.value) {
                try { api.updateMeal(meal.id, mapOf("isCollected" to updated.isCollected)) }
                catch (e: Exception) { Log.w("NutriViewModel", "Failed to update collection", e) }
            }
        }
    }

    fun clearAll() {
        viewModelScope.launch { repository.clear() }
    }

    // ── DTO mapping helpers ──

    private fun dtoToMeal(dto: MealListItemDto): Meal {
        return Meal(
            id = dto.id,
            title = dto.title,
            mealType = dto.mealTypeLabel,
            mealDate = dto.mealDate,
            dateString = dto.dateString,
            timeString = dto.timeString,
            calories = dto.calories,
            protein = dto.protein,
            carbs = dto.carbs,
            fat = dto.fat,
            imageUrl = dto.imageUrl,
            itemsJson = "[]"
        )
    }

    private fun mealToCreateDto(meal: Meal): CreateMealRequestDto {
        val mealType = when (meal.mealType) {
            "早餐" -> "breakfast"
            "午餐" -> "lunch"
            "晚餐" -> "dinner"
            "加餐" -> "snack"
            else -> meal.mealType.lowercase(Locale.US)
        }
        // Parse items from itemsJson
        val items = try {
            adapter.fromJson(meal.itemsJson) ?: emptyList()
        } catch (e: Exception) { emptyList() }

        return CreateMealRequestDto(
            title = meal.title,
            mealType = mealType,
            mealDate = meal.mealDate.ifEmpty { "2026-06-01" },
            timeString = meal.timeString,
            notes = meal.notes,
            imageUrl = meal.imageUrl,
            multiplier = meal.multiplier,
            isCollected = meal.isCollected,
            isLiked = meal.isLiked,
            healthScore = meal.healthScore,
            healthMessage = meal.healthMessage,
            source = "manual",
            items = items.map { CreateMealItemDto(
                name = it.name,
                calories = it.calories,
                weightString = it.weightString,
            )}
        )
    }

    companion object {
        private val DATE_DISPLAY_TO_ISO = mapOf(
            "5月15日" to "2026-05-15", "5月22日" to "2026-05-22",
            "5月25日" to "2026-05-25", "5月26日" to "2026-05-26",
            "5月27日" to "2026-05-27", "5月28日" to "2026-05-28",
            "5月29日" to "2026-05-29", "5月30日" to "2026-05-30",
            "5月31日" to "2026-05-31", "6月1日" to "2026-06-01",
            "6月2日" to "2026-06-02", "6月3日" to "2026-06-03",
            "6月4日" to "2026-06-04", "6月5日" to "2026-06-05",
            "6月6日" to "2026-06-06", "6月7日" to "2026-06-07",
            "6月8日" to "2026-06-08", "6月9日" to "2026-06-09",
            "6月10日" to "2026-06-10", "6月11日" to "2026-06-11",
            "6月12日" to "2026-06-12", "6月13日" to "2026-06-13",
            "6月14日" to "2026-06-14",
        )

        fun dateStringToIso(display: String): String {
            return DATE_DISPLAY_TO_ISO[display] ?: "2026-06-01"
        }

        private val ISO_TO_DISPLAY = DATE_DISPLAY_TO_ISO.entries.associate { it.value to it.key }

        fun isoToDateString(iso: String): String {
            return ISO_TO_DISPLAY[iso] ?: iso
        }
    }
}
