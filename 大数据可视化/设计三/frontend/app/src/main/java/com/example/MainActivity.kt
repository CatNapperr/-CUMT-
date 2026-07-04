package com.example

import android.content.Context
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.annotation.DrawableRes
import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.*
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.*
import androidx.compose.ui.graphics.*
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.Dialog
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import coil.compose.AsyncImage
import com.example.data.FoodItem
import com.example.data.Meal
import com.example.ui.theme.*
import com.example.ui.viewmodel.MainTab
import com.example.ui.viewmodel.NutriViewModel
import java.util.Locale
import java.util.UUID

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MyApplicationTheme {
                NutriApp()
            }
        }
    }
}

@OptIn(ExperimentalAnimationApi::class)
@Composable
fun NutriApp(viewModel: NutriViewModel = viewModel()) {
    val context = LocalContext.current
    val currentTab by viewModel.currentTab.collectAsStateWithLifecycle()
    val loggedMeals by viewModel.loggedMeals.collectAsStateWithLifecycle()
    val selectedDateStr by viewModel.selectedDateStr.collectAsStateWithLifecycle()
    val isAnalyzing by viewModel.isAnalyzing.collectAsStateWithLifecycle()
    val showMealDetailsOverlay by viewModel.showMealDetailsOverlay.collectAsStateWithLifecycle()
    val mealUnderReview by viewModel.mealUnderReview.collectAsStateWithLifecycle()
    val nutritionTargets by viewModel.nutritionTargets.collectAsStateWithLifecycle()

    var showQuickLogPill by remember { mutableStateOf(false) }
    var showSearchDialog by remember { mutableStateOf(false) }
    var showCameraSimulation by remember { mutableStateOf(false) }
    var showVoiceInputDialog by remember { mutableStateOf(false) }

    val todayMeals = loggedMeals.filter { it.dateString == selectedDateStr }
    val totalCaloriesToday = todayMeals.sumOf { it.calories }
    val deductActiveBurn by viewModel.deductActiveBurn.collectAsStateWithLifecycle()
    val targetCalories = nutritionTargets.targetCalories
    val extraBurn = if (deductActiveBurn) 350 else 0
    val remainingCalories = (targetCalories - totalCaloriesToday + extraBurn).coerceAtLeast(0)

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        bottomBar = {
            NutriBottomNavigationBar(
                currentTab = currentTab,
                onTabSelected = { viewModel.selectTab(it) },
                isOpen = showQuickLogPill,
                onAddClick = { showQuickLogPill = !showQuickLogPill }
            )
        },
        containerColor = DarkBackground
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .drawBehind {
                    // Holographic glow effects in the background for technological elegance
                    drawCircle(
                        brush = Brush.radialGradient(
                            colors = listOf(AccentOrange.copy(alpha = 0.08f), Color.Transparent),
                            center = Offset(size.width * 0.8f, size.height * 0.2f),
                            radius = 600f
                        )
                    )
                    drawCircle(
                        brush = Brush.radialGradient(
                            colors = listOf(AccentTeal.copy(alpha = 0.05f), Color.Transparent),
                            center = Offset(size.width * 0.1f, size.height * 0.6f),
                            radius = 800f
                        )
                    )
                }
        ) {
            // Tab content dispatcher
            AnimatedContent(
                targetState = currentTab,
                transitionSpec = {
                    fadeIn(animationSpec = tween(220)) with fadeOut(animationSpec = tween(220))
                },
                label = "TabTransition"
            ) { tab ->
                when (tab) {
                    MainTab.HOME -> HomeTab(viewModel, loggedMeals, selectedDateStr)
                    MainTab.DIARY -> DiaryTab(viewModel, loggedMeals, selectedDateStr)
                    MainTab.ANALYSIS -> AnalysisTab(viewModel, loggedMeals)
                    MainTab.PROFILE -> ProfileTab(nutritionTargets.targetCalories)
                }
            }

            // --- Custom Meal Details Sheet Overlay (Screen 1) ---
            if (showMealDetailsOverlay && mealUnderReview != null) {
                MealDetailsOverlay(
                    viewModel = viewModel,
                    meal = mealUnderReview!!,
                    onDismiss = { viewModel.cancelReview() }
                )
            }

            // --- Floating Quick Log Pill (as chosen by add click) ---
            AnimatedVisibility(
                visible = showQuickLogPill,
                enter = slideInVertically(initialOffsetY = { it }) + fadeIn(),
                exit = slideOutVertically(targetOffsetY = { it }) + fadeOut(),
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .padding(bottom = 16.dp, start = 16.dp, end = 16.dp)
            ) {
                QuickLogPill(
                    remainingCalories = remainingCalories,
                    onSearchClick = {
                        showSearchDialog = true
                        showQuickLogPill = false
                    },
                    onCameraClick = {
                        showCameraSimulation = true
                        showQuickLogPill = false
                    },
                    onVoiceClick = {
                        showVoiceInputDialog = true
                        showQuickLogPill = false
                    }
                )
            }

            // --- Quick Search food dialog ---
            if (showSearchDialog) {
                SearchFoodDialog(
                    loggedMeals = loggedMeals,
                    onDismiss = { showSearchDialog = false },
                    onSelectMeal = { meal ->
                        viewModel.openMealForReview(meal.copy(dateString = selectedDateStr))
                        showSearchDialog = false
                    }
                )
            }

            // --- Camera capture simulation dialog ---
            if (showCameraSimulation) {
                CameraSimulationDialog(
                    onDismiss = { showCameraSimulation = false },
                    onSuccessAdd = { simulatedMeal ->
                        viewModel.openMealForReview(simulatedMeal.copy(dateString = selectedDateStr))
                    }
                )
            }

            // --- Voice description input dialog ---
            if (showVoiceInputDialog) {
                AiAnalyzeDialog(
                    isAnalyzing = isAnalyzing,
                    onDismiss = { showVoiceInputDialog = false },
                    onAnalyze = { text ->
                        viewModel.analyzeAndReviewMeal(text)
                        showVoiceInputDialog = false
                    }
                )
            }
        }
    }
}

// --- TAB 1: HOME TAB (首页) ---

@Composable
fun HomeTab(
    viewModel: NutriViewModel,
    loggedMeals: List<Meal>,
    selectedDateStr: String
) {
    val deductActiveBurn by viewModel.deductActiveBurn.collectAsStateWithLifecycle()
    val nutritionTargets by viewModel.nutritionTargets.collectAsStateWithLifecycle()

    // Filter today's logged meals
    val mealsToday = loggedMeals.filter { it.dateString == selectedDateStr }
    val totalCaloriesToday = mealsToday.sumOf { it.calories }
    val totalProteinToday = mealsToday.sumOf { it.protein }
    val totalCarbsToday = mealsToday.sumOf { it.carbs }
    val totalFatToday = mealsToday.sumOf { it.fat }

    // Target calculation: target calorie from API/nutrition targets
    val targetCalories = nutritionTargets.targetCalories
    val extraBurn = if (deductActiveBurn) 350 else 0
    val remainingCalories = (targetCalories - totalCaloriesToday + extraBurn).coerceAtLeast(0)

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp),
        contentPadding = PaddingValues(top = 16.dp, bottom = 24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // --- 1. Top Header Bar ---
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    IconButton(
                        onClick = { /* Open menu */ },
                        modifier = Modifier
                            .size(40.dp)
                            .clip(CircleShape)
                            .background(CardSurface)
                    ) {
                        Icon(imageVector = Icons.Default.Menu, contentDescription = "Menu", tint = TextPrimary)
                    }
                    Spacer(modifier = Modifier.width(12.dp))
                    Text(
                        text = "NutriAI",
                        style = TextStyle(
                            fontFamily = FontFamily.Default,
                            fontWeight = FontWeight.Bold,
                            fontSize = 24.sp,
                            color = AccentOrange
                        )
                    )
                }

                Row(verticalAlignment = Alignment.CenterVertically) {
                    // Active Quality bubble
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(12.dp))
                            .background(AccentTeal.copy(alpha = 0.2f))
                            .border(1.dp, AccentTeal, RoundedCornerShape(12.dp))
                            .padding(horizontal = 10.dp, vertical = 4.dp)
                    ) {
                        Text(
                            text = "良好 B",
                            color = AccentTeal,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                    Spacer(modifier = Modifier.width(12.dp))
                    IconButton(
                        onClick = { /* Notifications */ },
                        modifier = Modifier
                            .size(40.dp)
                            .clip(CircleShape)
                            .background(CardSurface)
                    ) {
                        Icon(imageVector = Icons.Default.Notifications, contentDescription = "Notifications", tint = TextPrimary)
                    }
                }
            }
        }

        // --- 2. Scrollable Date Selector ---
        item {
            DateSelectorStrip(selectedDateStr) { date ->
                viewModel.setSelectedDate(date)
            }
        }

        // --- 3. Calorie Semicircular Gauge Card ---
        item {
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, Color.White.copy(alpha = 0.08f), RoundedCornerShape(24.dp)),
                colors = CardDefaults.cardColors(containerColor = CardSurface),
                shape = RoundedCornerShape(24.dp)
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    // Gauge container
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(150.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        SemicircularCalorieGauge(
                            eaten = totalCaloriesToday,
                            target = targetCalories + extraBurn,
                            color = AccentOrange
                        )
                        Column(
                            horizontalAlignment = Alignment.CenterHorizontally,
                            modifier = Modifier.offset(y = 20.dp)
                        ) {
                            Text(
                                text = "$remainingCalories",
                                style = TextStyle(
                                    fontWeight = FontWeight.Bold,
                                    fontSize = 44.sp,
                                    color = TextPrimary,
                                    letterSpacing = (-1).sp
                                )
                            )
                            Text(
                                text = "剩余千卡",
                                style = TextStyle(
                                    fontSize = 13.sp,
                                    color = TextSecondary
                                )
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(8.dp))

                    // Small Nutrient macro specs row
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceEvenly
                    ) {
                        NutrientHomeRowItem(
                            label = "蛋白质",
                            current = totalProteinToday,
                            target = nutritionTargets.protein,
                            unit = "g",
                            color = AccentTeal
                        )
                        NutrientHomeRowItem(
                            label = "碳水",
                            current = totalCarbsToday,
                            target = nutritionTargets.carbs,
                            unit = "g",
                            color = AccentPurple
                        )
                        NutrientHomeRowItem(
                            label = "脂肪",
                            current = totalFatToday,
                            target = nutritionTargets.fat,
                            unit = "g",
                            color = AccentYellow
                        )
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    // Indicator dots pagination (just decoration)
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        modifier = Modifier.align(Alignment.CenterHorizontally)
                    ) {
                        Box(modifier = Modifier.size(6.dp).clip(CircleShape).background(AccentOrange))
                        Box(modifier = Modifier.size(6.dp).clip(CircleShape).background(TextSecondary.copy(alpha = 0.3f)))
                        Box(modifier = Modifier.size(6.dp).clip(CircleShape).background(TextSecondary.copy(alpha = 0.3f)))
                    }
                }
            }
        }

        // --- 4. Today's Food Title ---
        item {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "今日餐食",
                    style = TextStyle(
                        fontWeight = FontWeight.Bold,
                        fontSize = 18.sp,
                        color = TextPrimary
                    )
                )
                Text(
                    text = "${mealsToday.size} 次记录",
                    color = TextSecondary,
                    fontSize = 12.sp
                )
            }
        }

        // --- 5. Logged Meals list ---
        if (mealsToday.isEmpty()) {
            item {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(160.dp)
                        .clip(RoundedCornerShape(16.dp))
                        .background(CardSurface)
                        .border(1.dp, Color.White.copy(alpha = 0.05f), RoundedCornerShape(16.dp)),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(
                            imageVector = Icons.Default.Restaurant,
                            contentDescription = "No foods",
                            tint = TextSecondary.copy(alpha = 0.4f),
                            modifier = Modifier.size(40.dp)
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                        Text(
                            text = "该日期暂未记录餐食",
                            color = TextSecondary,
                            fontSize = 14.sp
                        )
                        Text(
                            text = "点击下方的 '+' 号开始 AI 分析！",
                            color = TextSecondary.copy(alpha = 0.6f),
                            fontSize = 12.sp,
                            modifier = Modifier.padding(top = 4.dp)
                        )
                    }
                }
            }
        } else {
            items(mealsToday) { meal ->
                MealCardItem(meal = meal, onClick = {
                    viewModel.openMealForReview(meal)
                })
            }
        }
    }
}

@Composable
fun DateSelectorStrip(selectedDate: String, onDateSelected: (String) -> Unit) {
    val dates = listOf(
        "5月26日" to "Tu",
        "5月27日" to "We",
        "5月28日" to "Th",
        "5月29日" to "Fr",
        "5月30日" to "Sa",
        "5月31日" to "Su",
        "6月1日" to "Mo"
    )

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        dates.forEach { (date, label) ->
            val isSelected = date == selectedDate
            val borderModifier = if (isSelected) {
                Modifier.border(
                    BorderStroke(1.5.dp, SolidColor(AccentOrange)),
                    shape = RoundedCornerShape(14.dp)
                )
            } else Modifier

            Column(
                modifier = Modifier
                    .width(48.dp)
                    .clip(RoundedCornerShape(14.dp))
                    .then(borderModifier)
                    .background(if (isSelected) AccentOrange.copy(alpha = 0.15f) else Color.Transparent)
                    .clickable { onDateSelected(date) }
                    .padding(vertical = 10.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Text(
                    text = label,
                    color = if (isSelected) AccentOrange else TextSecondary,
                    fontSize = 12.sp,
                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal
                )
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = date.substringAfter("月").substringBefore("日"),
                    color = if (isSelected) TextPrimary else TextSecondary,
                    fontSize = 15.sp,
                    fontWeight = FontWeight.Bold
                )
                if (isSelected) {
                    Box(
                        modifier = Modifier
                            .padding(top = 6.dp)
                            .size(4.dp)
                            .clip(CircleShape)
                            .background(AccentOrange)
                    )
                }
            }
        }
    }
}

@Composable
fun SemicircularCalorieGauge(eaten: Int, target: Int, color: Color) {
    val animatedProgress = remember { Animatable(0f) }
    LaunchedEffect(eaten, target) {
        val fraction = if (target > 0) eaten.toFloat() / target else 0f
        animatedProgress.animateTo(
            targetValue = fraction.coerceIn(0f, 1.1f),
            animationSpec = tween(durationMillis = 1000, easing = FastOutSlowInEasing)
        )
    }

    Canvas(modifier = Modifier.fillMaxSize()) {
        val strokeWidth = 14.dp.toPx()
        val diameter = size.height * 2 - strokeWidth
        val topLeft = Offset((size.width - diameter) / 2f, strokeWidth / 2f)
        val arcSize = Size(diameter, diameter)

        // 1. Background arc
        drawArc(
            color = Color.White.copy(alpha = 0.08f),
            startAngle = 180f,
            sweepAngle = 180f,
            useCenter = false,
            topLeft = topLeft,
            size = arcSize,
            style = Stroke(width = strokeWidth, cap = StrokeCap.Round)
        )

        // 2. Main color arc
        drawArc(
            brush = Brush.horizontalGradient(
                colors = listOf(color, color.copy(alpha = 0.5f))
            ),
            startAngle = 180f,
            sweepAngle = 180f * animatedProgress.value,
            useCenter = false,
            topLeft = topLeft,
            size = arcSize,
            style = Stroke(width = strokeWidth, cap = StrokeCap.Round)
        )
    }
}

@Composable
fun NutrientHomeRowItem(label: String, current: Int, target: Int, unit: String, color: Color) {
    val fraction = if (target > 0) current.toFloat() / target else 0f
    val animatedFraction = animateFloatAsState(targetValue = fraction.coerceIn(0f, 1f), label = "MacroAnimate")

    Column(
        modifier = Modifier.width(84.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Row(
            verticalAlignment = Alignment.Bottom,
            horizontalArrangement = Arrangement.Center
        ) {
            Text(
                text = "$current",
                color = TextPrimary,
                fontWeight = FontWeight.Bold,
                fontSize = 15.sp
            )
            Text(
                text = unit,
                color = TextSecondary,
                fontSize = 11.sp,
                modifier = Modifier.padding(bottom = 1.dp)
            )
        }
        Spacer(modifier = Modifier.height(4.dp))
        // Progress bar line
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(4.dp)
                .clip(CircleShape)
                .background(Color.White.copy(alpha = 0.08f))
        ) {
            Box(
                modifier = Modifier
                    .fillMaxHeight()
                    .fillMaxWidth(animatedFraction.value)
                    .clip(CircleShape)
                    .background(color)
            )
        }
        Spacer(modifier = Modifier.height(4.dp))
        Text(text = label, color = TextSecondary, fontSize = 11.sp)
    }
}

@Composable
fun MealCardItem(meal: Meal, onClick: () -> Unit) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() }
            .border(1.dp, Color.White.copy(alpha = 0.05f), RoundedCornerShape(16.dp)),
        colors = CardDefaults.cardColors(containerColor = CardSurface),
        shape = RoundedCornerShape(16.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Food photo Coil Image
            Box(
                modifier = Modifier
                    .size(80.dp)
                    .clip(RoundedCornerShape(12.dp))
                    .background(Color.White.copy(alpha = 0.05f)),
                contentAlignment = Alignment.Center
            ) {
                if (meal.imageUrl != null) {
                    AsyncImage(
                        model = meal.imageUrl,
                        contentDescription = meal.title,
                        contentScale = ContentScale.Crop,
                        modifier = Modifier.fillMaxSize()
                    )
                } else {
                    Icon(
                        imageVector = Icons.Default.Fastfood,
                        contentDescription = "Meal Photo",
                        tint = TextSecondary.copy(alpha = 0.4f)
                    )
                }
                // Timestamp Overlay block
                Box(
                    modifier = Modifier
                        .align(Alignment.BottomStart)
                        .background(Color.Black.copy(alpha = 0.6f))
                        .padding(horizontal = 6.dp, vertical = 2.dp)
                ) {
                    Text(text = meal.timeString, color = Color.White, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                }
            }

            Spacer(modifier = Modifier.width(16.dp))

            // Text specs
            Column(
                modifier = Modifier.weight(1f)
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = meal.title,
                        color = TextPrimary,
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier.weight(1f)
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(8.dp))
                            .background(Color.White.copy(alpha = 0.08f))
                            .padding(horizontal = 6.dp, vertical = 2.dp)
                    ) {
                        Text(text = meal.mealType, color = TextSecondary, fontSize = 10.sp)
                    }
                }

                Spacer(modifier = Modifier.height(10.dp))

                // Detail specs calories + macro row
                Row(
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "${meal.calories} 千卡",
                        color = TextPrimary,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                    Spacer(modifier = Modifier.width(12.dp))
                    Text(text = "℗ ${meal.protein}g", color = AccentTeal, fontSize = 12.sp)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(text = "© ${meal.carbs}g", color = AccentPurple, fontSize = 12.sp)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(text = "Ⓨ ${meal.fat}g", color = AccentYellow, fontSize = 12.sp)
                }
            }
        }
    }
}

// --- TAB 2: DIARY TAB (日记) ---

@Composable
fun DiaryTab(
    viewModel: NutriViewModel,
    loggedMeals: List<Meal>,
    selectedDateStr: String
) {
    val mealsToday = loggedMeals.filter { it.dateString == selectedDateStr }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp)
    ) {
        Spacer(modifier = Modifier.height(16.dp))

        // Header Title
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "照片日记",
                style = TextStyle(
                    fontWeight = FontWeight.Bold,
                    fontSize = 24.sp,
                    color = AccentOrange
                )
            )
            IconButton(
                onClick = { /* Settings */ },
                modifier = Modifier
                    .size(40.dp)
                    .clip(CircleShape)
                    .background(CardSurface)
            ) {
                Icon(imageVector = Icons.Default.CalendarMonth, contentDescription = "Calendar view", tint = TextPrimary)
            }
        }

        Spacer(modifier = Modifier.height(16.dp))
        
        // Date Strip
        DateSelectorStrip(selectedDateStr) { date ->
            viewModel.setSelectedDate(date)
        }

        Spacer(modifier = Modifier.height(16.dp))

        if (mealsToday.isEmpty()) {
            EmptyDiaryState()
        } else {
            // Photo grid view!
            LazyVerticalGrid(
                mealsToday = mealsToday,
                onMealClick = { viewModel.openMealForReview(it) }
            )
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun LazyVerticalGrid(mealsToday: List<Meal>, onMealClick: (Meal) -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(
            text = "已拍照片",
            fontSize = 16.sp,
            fontWeight = FontWeight.Bold,
            color = TextSecondary
        )

        // FlowRow: 3 items per row with wrapping
        FlowRow(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            maxItemsInEachRow = 3,
        ) {
            mealsToday.forEach { meal ->
                Box(
                    modifier = Modifier
                        .width(0.dp)
                        .weight(1f)
                        .aspectRatio(1f)
                        .clip(RoundedCornerShape(16.dp))
                        .border(1.dp, Color.White.copy(alpha = 0.08f), RoundedCornerShape(16.dp))
                        .clickable { onMealClick(meal) }
                ) {
                    if (meal.imageUrl != null) {
                        AsyncImage(
                            model = meal.imageUrl,
                            contentDescription = meal.title,
                            contentScale = ContentScale.Crop,
                            modifier = Modifier.fillMaxSize()
                        )
                    } else {
                        Box(
                            modifier = Modifier
                                .fillMaxSize()
                                .background(CardSurface),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(imageVector = Icons.Default.Fastfood, contentDescription = "dish", tint = TextSecondary)
                        }
                    }

                    // Bottom info label overlay
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .align(Alignment.BottomStart)
                            .background(Color.Black.copy(alpha = 0.65f))
                            .padding(8.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = meal.timeString,
                                color = Color.White,
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold
                            )
                            Text(
                                text = "${meal.calories}kcal",
                                color = AccentOrange,
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun ColumnScope.EmptyDiaryState() {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .weight(1f),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.padding(24.dp)
        ) {
            Icon(
                imageVector = Icons.Default.LocalActivity, // representing peach icon simply for neat layout
                contentDescription = "No images",
                tint = AccentOrange.copy(alpha = 0.4f),
                modifier = Modifier.size(56.dp)
            )
            Spacer(modifier = Modifier.height(16.dp))
            Text(
                text = "还没有记录",
                color = TextPrimary,
                fontWeight = FontWeight.Bold,
                fontSize = 18.sp
            )
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = "系统未在该日期检测到拍摄的饮食照片",
                color = TextSecondary,
                fontSize = 14.sp,
                textAlign = TextAlign.Center
            )
            Text(
                text = "开始记录你的第一餐吧！",
                color = AccentOrange.copy(alpha = 0.8f),
                fontSize = 13.sp,
                textAlign = TextAlign.Center,
                modifier = Modifier.padding(top = 4.dp)
            )
        }
    }
}

// --- TAB 3: ANALYSIS TAB (分析) ---

data class WeekData(
    val dateRangeLabel: String,
    val startIso: String,
    val endIso: String,
    val dayDates: List<String>,
    val dayLabels: List<String>
)

enum class AnalysisMetric(val label: String, val unit: String) {
    CALORIES("卡路里", "千卡"),
    FAT("脂肪", "克"),
    CARBS("碳水", "克"),
    PROTEIN("蛋白质", "克")
}

val weeksData = listOf(
    WeekData(
        "2026年5月11日 - 2026年5月17日", "2026-05-11", "2026-05-17",
        listOf("5月11日", "5月12日", "5月13日", "5月14日", "5月15日", "5月16日", "5月17日"),
        listOf("周一\n5/11", "周二\n5/12", "周三\n5/13", "周四\n5/14", "周五\n5/15", "周六\n5/16", "周日\n5/17")
    ),
    WeekData(
        "2026年5月18日 - 2026年5月24日", "2026-05-18", "2026-05-24",
        listOf("5月18日", "5月19日", "5月20日", "5月21日", "5月22日", "5月23日", "5月24日"),
        listOf("周一\n5/18", "周二\n5/19", "周三\n5/20", "周四\n5/21", "周五\n5/22", "周六\n5/23", "周日\n5/24")
    ),
    WeekData(
        "2026年5月25日 - 2026年5月31日", "2026-05-25", "2026-05-31",
        listOf("5月25日", "5月26日", "5月27日", "5月28日", "5月29日", "5月30日", "5月31日"),
        listOf("周一\n5/25", "周二\n5/26", "周三\n5/27", "周四\n5/28", "周五\n5/29", "周六\n5/30", "周日\n5/31")
    ),
    WeekData(
        "2026年6月1日 - 2026年6月7日", "2026-06-01", "2026-06-07",
        listOf("6月1日", "6月2日", "6月3日", "6月4日", "6月5日", "6月6日", "6月7日"),
        listOf("周一\n6/1", "周二\n6/2", "周三\n6/3", "周四\n6/4", "周五\n6/5", "周六\n6/6", "周日\n6/7")
    ),
    WeekData(
        "2026年6月8日 - 2026年6月14日", "2026-06-08", "2026-06-14",
        listOf("6月8日", "6月9日", "6月10日", "6月11日", "6月12日", "6月13日", "6月14日"),
        listOf("周一\n6/8", "周二\n6/9", "周三\n6/10", "周四\n6/11", "周五\n6/12", "周六\n6/13", "周日\n6/14")
    )
)

@Composable
fun AnalysisTab(viewModel: NutriViewModel, loggedMeals: List<Meal>) {
    val context = LocalContext.current
    val deductActiveBurn by viewModel.deductActiveBurn.collectAsStateWithLifecycle()
    val weekAnalytics by viewModel.weekAnalytics.collectAsStateWithLifecycle()
    val nutritionTargets by viewModel.nutritionTargets.collectAsStateWithLifecycle()

    var activeWeekIndex by remember { mutableStateOf(2) } // default is 5/25 - 5/31
    val activeWeek = weeksData[activeWeekIndex]

    var showDropdown by remember { mutableStateOf(false) }
    var selectedMetric by remember { mutableStateOf(AnalysisMetric.CALORIES) }

    // Sync week navigation to ViewModel (triggers API calls)
    LaunchedEffect(activeWeekIndex) {
        val week = weeksData[activeWeekIndex]
        viewModel.setWeekRange(week.startIso, week.endIso)
    }

    val mealsInActiveWeek = loggedMeals.filter { it.dateString in activeWeek.dayDates }

    val metricLabel = selectedMetric.label
    val metricUnit = selectedMetric.unit

    // Use API weekAnalytics when available, fall back to local calculations
    val recordedDaysInWeek = weekAnalytics?.recordedDays
        ?: activeWeek.dayDates.count { dateStr ->
            loggedMeals.any { it.dateString == dateStr }
        }

    val totalMetricValue = mealsInActiveWeek.sumOf { meal ->
        when (selectedMetric) {
            AnalysisMetric.CALORIES -> meal.calories
            AnalysisMetric.FAT -> meal.fat.toDouble().toInt()
            AnalysisMetric.CARBS -> meal.carbs.toDouble().toInt()
            AnalysisMetric.PROTEIN -> meal.protein.toDouble().toInt()
        }
    }

    val avgMetricValue = weekAnalytics?.averageValue
        ?: if (recordedDaysInWeek > 0) totalMetricValue / recordedDaysInWeek else 0
    val avgMetricStr = "$avgMetricValue $metricUnit"

    val targetMetricValue = weekAnalytics?.targetValue
        ?: when (selectedMetric) {
            AnalysisMetric.CALORIES -> nutritionTargets.targetCalories
            AnalysisMetric.FAT -> nutritionTargets.fat
            AnalysisMetric.CARBS -> nutritionTargets.carbs
            AnalysisMetric.PROTEIN -> nutritionTargets.protein
        }
    val targetMetricStr = "$targetMetricValue $metricUnit"

    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp),
        contentPadding = PaddingValues(top = 16.dp, bottom = 24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // --- 1. Week Selector bar ---
        item {
            Card(
                colors = CardDefaults.cardColors(containerColor = CardSurface),
                shape = RoundedCornerShape(16.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, Color.White.copy(alpha = 0.05f), RoundedCornerShape(16.dp))
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(12.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    IconButton(
                        onClick = { if (activeWeekIndex > 0) activeWeekIndex-- },
                        enabled = activeWeekIndex > 0
                    ) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "back",
                            tint = if (activeWeekIndex > 0) TextPrimary else TextSecondary.copy(alpha = 0.3f)
                        )
                    }
                    Text(
                        text = activeWeek.dateRangeLabel,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary,
                        fontSize = 14.sp
                    )
                    IconButton(
                        onClick = { if (activeWeekIndex < weeksData.lastIndex) activeWeekIndex++ },
                        enabled = activeWeekIndex < weeksData.lastIndex
                    ) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowForward,
                            contentDescription = "forward",
                            tint = if (activeWeekIndex < weeksData.lastIndex) TextPrimary else TextSecondary.copy(alpha = 0.3f)
                        )
                    }
                }
            }
        }

        // --- 2. Calories/Metric Column Chart ---
        item {
            Card(
                colors = CardDefaults.cardColors(containerColor = CardSurface),
                shape = RoundedCornerShape(20.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, Color.White.copy(alpha = 0.05f), RoundedCornerShape(20.dp))
            ) {
                Column(
                    modifier = Modifier.padding(20.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.Start,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Box(modifier = Modifier.wrapContentSize()) {
                            Box(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(8.dp))
                                    .background(Color.White.copy(alpha = 0.08f))
                                    .clickable { showDropdown = true }
                                    .padding(horizontal = 12.dp, vertical = 8.dp)
                            ) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Text(text = "$metricLabel ▾", color = TextPrimary, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                                }
                            }
                            
                            DropdownMenu(
                                expanded = showDropdown,
                                onDismissRequest = { showDropdown = false },
                                modifier = Modifier
                                    .background(CardSurface)
                                    .border(1.dp, Color.White.copy(alpha = 0.1f), RoundedCornerShape(8.dp))
                            ) {
                                AnalysisMetric.values().forEach { metric ->
                                    DropdownMenuItem(
                                        text = { Text(metric.label, color = TextPrimary, fontSize = 13.sp) },
                                        onClick = {
                                            selectedMetric = metric
                                            showDropdown = false
                                            viewModel.setAnalyticsMetric(metric.name.lowercase(Locale.US))
                                        }
                                    )
                                }
                            }
                        }
                    }

                    // Weekly Bar Chart based on selected week + selected metric
                    CalorieBarChart(
                        selectedWeek = activeWeek,
                        loggedMeals = loggedMeals,
                        metric = selectedMetric,
                        targetValue = targetMetricValue
                    )

                    // Statistics Board
                    Column(
                        verticalArrangement = Arrangement.spacedBy(10.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(Color.White.copy(alpha = 0.02f), RoundedCornerShape(12.dp))
                            .padding(14.dp)
                    ) {
                        Row(
                            horizontalArrangement = Arrangement.SpaceBetween,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(text = "已记录天数:", color = TextSecondary, fontSize = 13.sp)
                            Text(text = "$recordedDaysInWeek 天", color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                        }
                        Row(
                            horizontalArrangement = Arrangement.SpaceBetween,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(text = "日均 $metricLabel:", color = TextSecondary, fontSize = 13.sp)
                            Text(text = avgMetricStr, color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                        }
                        Row(
                            horizontalArrangement = Arrangement.SpaceBetween,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(text = "每日目标:", color = TextSecondary, fontSize = 13.sp)
                            Text(text = targetMetricStr, color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                        }
                        Row(
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(text = "扣除活动消耗:", color = TextSecondary, fontSize = 13.sp)
                            Switch(
                                checked = deductActiveBurn,
                                onCheckedChange = { viewModel.toggleActiveBurn() },
                                colors = SwitchDefaults.colors(
                                    checkedThumbColor = AccentTeal,
                                    checkedTrackColor = AccentTeal.copy(alpha = 0.4f)
                                )
                            )
                        }
                    }
                }
            }
        }

        // --- 3. Nutrient stacked ratio chart ---
        item {
            Card(
                colors = CardDefaults.cardColors(containerColor = CardSurface),
                shape = RoundedCornerShape(20.dp),
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, Color.White.copy(alpha = 0.05f), RoundedCornerShape(20.dp))
            ) {
                Column(
                    modifier = Modifier.padding(20.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    Text(
                        text = "营养素分布 (%)",
                        color = TextPrimary,
                        fontWeight = FontWeight.Bold,
                        fontSize = 16.sp
                    )

                    // Color Legends Row
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(16.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        LegendDot(color = AccentPurple, label = "脂肪")
                        LegendDot(color = AccentTeal, label = "碳水")
                        LegendDot(color = AccentYellow, label = "蛋白质")
                    }

                    // Stacked proportions bars
                    StackedBarChart(
                        selectedWeek = activeWeek,
                        loggedMeals = loggedMeals
                    )

                    // Dynamic average pill panel
                    val fatSumTotal = mealsInActiveWeek.sumOf { it.fat.toDouble() }
                    val carbsSumTotal = mealsInActiveWeek.sumOf { it.carbs.toDouble() }
                    val proteinSumTotal = mealsInActiveWeek.sumOf { it.protein.toDouble() }
                    val totalGramsTotal = fatSumTotal + carbsSumTotal + proteinSumTotal

                    val fatPf = if (totalGramsTotal > 0) (fatSumTotal / totalGramsTotal).toFloat() else 0.32f
                    val carbsPf = if (totalGramsTotal > 0) (carbsSumTotal / totalGramsTotal).toFloat() else 0.34f
                    val proteinPf = if (totalGramsTotal > 0) 1.0f - fatPf - carbsPf else 0.34f

                    val fatPercent = (fatPf * 100).toInt()
                    val carbsPercent = (carbsPf * 100).toInt()
                    val proteinPercent = (proteinPf * 100).toInt()

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(text = "本周均值:", color = TextSecondary, fontSize = 12.sp, modifier = Modifier.align(Alignment.CenterVertically))
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            AveragePill(color = AccentPurple.copy(alpha = 0.15f), textColor = AccentPurple, label = "$fatPercent% 脂肪")
                            AveragePill(color = AccentTeal.copy(alpha = 0.15f), textColor = AccentTeal, label = "$carbsPercent% 碳水")
                            AveragePill(color = AccentYellow.copy(alpha = 0.15f), textColor = AccentYellow, label = "$proteinPercent% 蛋白")
                        }
                    }
                }
            }
        }

        // --- 4. Export button ---
        item {
            Button(
                onClick = {
                    Toast.makeText(context, "报告数据已成功导出为 NutriAI_Report.csv!", Toast.LENGTH_LONG).show()
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(52.dp),
                colors = ButtonDefaults.buttonColors(containerColor = CardSurface),
                border = BorderStroke(1.dp, AccentOrange),
                shape = RoundedCornerShape(14.dp)
            ) {
                Icon(imageVector = Icons.Default.Share, contentDescription = "export", tint = AccentOrange, modifier = Modifier.size(18.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text(text = "导出数据", color = AccentOrange, fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
fun LegendDot(color: Color, label: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(modifier = Modifier.size(10.dp).clip(CircleShape).background(color))
        Spacer(modifier = Modifier.width(6.dp))
        Text(text = label, color = TextSecondary, fontSize = 12.sp)
    }
}

@Composable
fun AveragePill(color: Color, textColor: Color, label: String) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(8.dp))
            .background(color)
            .padding(horizontal = 8.dp, vertical = 4.dp)
    ) {
        Text(text = label, color = textColor, fontSize = 11.sp, fontWeight = FontWeight.Bold)
    }
}

@Composable
fun CalorieBarChart(
    selectedWeek: WeekData,
    loggedMeals: List<Meal>,
    metric: AnalysisMetric,
    targetValue: Int
) {
    val metricColor = when (metric) {
        AnalysisMetric.CALORIES -> AccentOrange
        AnalysisMetric.FAT -> AccentPurple
        AnalysisMetric.CARBS -> AccentTeal
        AnalysisMetric.PROTEIN -> AccentYellow
    }

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(145.dp)
            .padding(vertical = 8.dp),
        horizontalArrangement = Arrangement.SpaceAround,
        verticalAlignment = Alignment.Bottom
    ) {
        selectedWeek.dayDates.forEachIndexed { index, dayDate ->
            val dayLabel = selectedWeek.dayLabels[index]
            val mealsForDay = loggedMeals.filter { it.dateString == dayDate }
            
            val dayValue = when (metric) {
                AnalysisMetric.CALORIES -> mealsForDay.sumOf { it.calories }
                AnalysisMetric.FAT -> mealsForDay.sumOf { it.fat.toDouble() }.toInt()
                AnalysisMetric.CARBS -> mealsForDay.sumOf { it.carbs.toDouble() }.toInt()
                AnalysisMetric.PROTEIN -> mealsForDay.sumOf { it.protein.toDouble() }.toInt()
            }

            val hasValue = dayValue > 0
            val textHighlight = if (hasValue) TextPrimary else TextSecondary
            val barBackground = if (hasValue) metricColor else Color.White.copy(alpha = 0.04f)
            
            val visualHeightFraction = if (dayValue > 0) {
                (dayValue.toFloat() / targetValue).coerceIn(0.12f, 1.0f)
            } else 0.02f

            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Bottom,
                modifier = Modifier
                    .fillMaxHeight()
                    .width(36.dp)
            ) {
                if (hasValue) {
                    Box(
                        modifier = Modifier
                            .background(metricColor, RoundedCornerShape(4.dp))
                            .padding(horizontal = 4.dp, vertical = 2.dp)
                    ) {
                        Text(
                            text = "$dayValue",
                            color = if (metricColor == AccentYellow) Color.Black else Color.White,
                            fontSize = 9.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                    Spacer(modifier = Modifier.height(4.dp))
                }

                Box(
                    modifier = Modifier
                        .weight(1f)
                        .width(16.dp)
                        .clip(RoundedCornerShape(topStart = 6.dp, topEnd = 6.dp))
                        .background(barBackground)
                        .fillMaxHeight(visualHeightFraction)
                )

                Spacer(modifier = Modifier.height(8.dp))

                Text(
                    text = dayLabel,
                    color = textHighlight,
                    fontSize = 10.sp,
                    lineHeight = 13.sp,
                    textAlign = TextAlign.Center,
                    fontWeight = if (hasValue) FontWeight.Bold else FontWeight.Normal
                )
            }
        }
    }
}

@Composable
fun StackedBarChart(
    selectedWeek: WeekData,
    loggedMeals: List<Meal>
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(180.dp)
            .padding(vertical = 8.dp),
        horizontalArrangement = Arrangement.SpaceAround,
        verticalAlignment = Alignment.Bottom
    ) {
        selectedWeek.dayDates.forEachIndexed { index, dayDate ->
            val dayLabel = selectedWeek.dayLabels[index]
            val mealsForDay = loggedMeals.filter { it.dateString == dayDate }

            val fatSum = mealsForDay.sumOf { it.fat.toDouble() }
            val carbsSum = mealsForDay.sumOf { it.carbs.toDouble() }
            val proteinSum = mealsForDay.sumOf { it.protein.toDouble() }
            val totalGrams = fatSum + carbsSum + proteinSum

            val hasValue = totalGrams > 0
            val textHighlight = if (hasValue) TextPrimary else TextSecondary
            val borderModifier = if (hasValue) Modifier.border(1.dp, Color.White.copy(alpha = 0.3f), RoundedCornerShape(6.dp)) else Modifier

            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Bottom,
                modifier = Modifier
                    .fillMaxHeight()
                    .width(36.dp)
            ) {
                // Stacked bar
                Column(
                    modifier = Modifier
                        .weight(1f)
                        .width(20.dp)
                        .clip(RoundedCornerShape(6.dp))
                        .then(borderModifier)
                ) {
                    if (hasValue) {
                        val fatWeight = (fatSum / totalGrams).toFloat()
                        val carbsWeight = (carbsSum / totalGrams).toFloat()
                        val proteinWeight = (proteinSum / totalGrams).toFloat()

                        val totalWeight = fatWeight + carbsWeight + proteinWeight
                        val fW = if (totalWeight > 0) fatWeight / totalWeight else 0.33f
                        val cW = if (totalWeight > 0) carbsWeight / totalWeight else 0.33f
                        val pW = if (totalWeight > 0) proteinWeight / totalWeight else 0.34f

                        if (fW > 0.05f) {
                            Box(modifier = Modifier.weight(fW).fillMaxWidth().background(AccentPurple), contentAlignment = Alignment.Center) {
                                if (fW >= 0.15f) Text("${(fW * 100).toInt()}%", color = Color.White, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                        if (cW > 0.04f) {
                            Box(modifier = Modifier.weight(cW).fillMaxWidth().background(AccentTeal), contentAlignment = Alignment.Center) {
                                if (cW >= 0.15f) Text("${(cW * 100).toInt()}%", color = Color.Black, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                        if (pW > 0.04f) {
                            Box(modifier = Modifier.weight(pW).fillMaxWidth().background(AccentYellow), contentAlignment = Alignment.Center) {
                                if (pW >= 0.15f) Text("${(pW * 100).toInt()}%", color = Color.Black, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                            }
                        }
                    } else {
                        Box(
                            modifier = Modifier
                                .fillMaxSize()
                                .background(Color.White.copy(alpha = 0.04f))
                        )
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))

                Text(
                    text = dayLabel,
                    color = textHighlight,
                    fontSize = 10.sp,
                    lineHeight = 13.sp,
                    textAlign = TextAlign.Center,
                    fontWeight = if (hasValue) FontWeight.Bold else FontWeight.Normal
                )
            }
        }
    }
}

// --- TAB 4: PROFILE TAB (我的) ---

@Composable
fun ProfileTab(targetCalories: Int = 2391) {
    val context = LocalContext.current
    LazyColumn(
        modifier = Modifier
            .fillMaxSize()
            .padding(horizontal = 20.dp),
        contentPadding = PaddingValues(top = 24.dp, bottom = 24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        // --- 1. Top Avatar Profile Panel ---
        item {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 12.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Box(
                    modifier = Modifier
                        .size(90.dp)
                        .clip(CircleShape)
                        .background(AccentTeal.copy(alpha = 0.15f))
                        .border(2.dp, AccentTeal, CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.Person,
                        contentDescription = "User avatar",
                        tint = AccentTeal,
                        modifier = Modifier.size(50.dp)
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                Text(
                    text = "王志豪",
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold,
                    color = TextPrimary
                )

                Spacer(modifier = Modifier.height(4.dp))

                Text(
                    text = "NutriAI Pro Member",
                    fontSize = 13.sp,
                    color = TextSecondary
                )
            }
        }

        // --- 2. Menu Group 1: Configuration ---
        item {
            ItemGroupPanel(
                listOf(
                    GridMenuItem(Icons.Default.Settings, "设置") {
                        Toast.makeText(context, "设置加载中...", Toast.LENGTH_SHORT).show()
                    },
                    GridMenuItem(Icons.Default.AccountCircle, "个人档案") {
                        Toast.makeText(context, "个人档案正在加载...", Toast.LENGTH_SHORT).show()
                    },
                    GridMenuItem(Icons.Default.RestaurantMenu, "查找食谱") {
                        Toast.makeText(context, "正在为您检索食谱数据库...", Toast.LENGTH_SHORT).show()
                    }
                )
            )
        }

        // --- 3. Menu Group 2: Features tracking ---
        item {
            ItemGroupPanel(
                listOf(
                    GridMenuItem(Icons.Default.NotificationAdd, "通知") {
                        Toast.makeText(context, "通知偏好设置", Toast.LENGTH_SHORT).show()
                    },
                    GridMenuItem(Icons.Default.TrendingUp, "体重追踪") {
                        Toast.makeText(context, "进入体重记录看板...", Toast.LENGTH_SHORT).show()
                    },
                    GridMenuItem(Icons.Default.LocalFireDepartment, "热量目标") {
                        Toast.makeText(context, "设置每日目标热量: ${targetCalories}kcal", Toast.LENGTH_SHORT).show()
                    },
                    GridMenuItem(Icons.Default.Favorite, "我的收藏") {
                        Toast.makeText(context, "正在拉取您收藏的美食餐食...", Toast.LENGTH_SHORT).show()
                    }
                )
            )
        }

        // --- 4. Menu Group 3: Help ---
        item {
            ItemGroupPanel(
                listOf(
                    GridMenuItem(Icons.Default.CardGiftcard, "邀请码") {
                        Toast.makeText(context, "您的分享专属邀请码: NUTRI592", Toast.LENGTH_LONG).show()
                    },
                    GridMenuItem(Icons.Default.QuestionMark, "帮助") {
                        Toast.makeText(context, "打开反馈帮助文档...", Toast.LENGTH_SHORT).show()
                    }
                )
            )
        }
    }
}

data class GridMenuItem(val icon: ImageVector, val label: String, val onClick: () -> Unit)

@Composable
fun ItemGroupPanel(items: List<GridMenuItem>) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .border(1.dp, Color.White.copy(alpha = 0.05f), RoundedCornerShape(16.dp)),
        colors = CardDefaults.cardColors(containerColor = CardSurface),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column {
            items.forEachIndexed { idx, item ->
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { item.onClick() }
                        .padding(horizontal = 16.dp, vertical = 14.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(imageVector = item.icon, contentDescription = item.label, tint = AccentTeal, modifier = Modifier.size(20.dp))
                        Spacer(modifier = Modifier.width(16.dp))
                        Text(text = item.label, color = TextPrimary, fontSize = 14.sp)
                    }
                    Icon(imageVector = Icons.Default.ChevronRight, contentDescription = "Arrow", tint = TextSecondary.copy(alpha = 0.5f), modifier = Modifier.size(16.dp))
                }

                if (idx < items.lastIndex) {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(1.dp)
                            .background(Color.White.copy(alpha = 0.05f))
                    )
                }
            }
        }
    }
}

// --- SIDE MODALS / SHEETS ---

// Screen 1: "您的餐食" Detailed review sheet overlay
@OptIn(ExperimentalLayoutApi::class)
@Composable
fun MealDetailsOverlay(
    viewModel: NutriViewModel,
    meal: Meal,
    onDismiss: () -> Unit
) {
    val context = LocalContext.current
    
    // Read state from VM
    val reviewedItems by viewModel.reviewedItems.collectAsStateWithLifecycle()
    val reviewedNotes by viewModel.reviewedNotes.collectAsStateWithLifecycle()
    val portionScale by viewModel.portionScale.collectAsStateWithLifecycle()
    val reviewedIsCollected by viewModel.reviewedIsCollected.collectAsStateWithLifecycle()
    val reviewedIsLiked by viewModel.reviewedIsLiked.collectAsStateWithLifecycle()

    var showAddFoodDialog by remember { mutableStateOf(false) }
    var keyMicrosExpanded by remember { mutableStateOf(false) }

    // Computes scaled metrics for indicators
    val scaleFactor = portionScale.toFloat()
    val scaledCalories = (meal.calories * scaleFactor).toInt()
    val scaledProtein = (meal.protein * scaleFactor).toInt()
    val scaledCarbs = (meal.carbs * scaleFactor).toInt()
    val scaledFat = (meal.fat * scaleFactor).toInt()

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black.copy(alpha = 0.7f)) // Translucent modal background dimmer
            .clickable(
                interactionSource = remember { MutableInteractionSource() },
                indication = null
            ) { /* block background taps from dismissing if misclicked */ }
    ) {
        // Sliding core box container matching standard design spec with 24.dp radius
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .fillMaxHeight(0.92f)
                .align(Alignment.BottomCenter)
                .border(2.dp, Color.White.copy(alpha = 0.08f), RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp)),
            shape = RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp),
            colors = CardDefaults.cardColors(containerColor = DarkBackground)
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
            ) {
                // Top drag handle decorative line
                Box(
                    modifier = Modifier
                        .padding(vertical = 12.dp)
                        .width(48.dp)
                        .height(4.dp)
                        .clip(CircleShape)
                        .background(TextSecondary.copy(alpha = 0.3f))
                        .align(Alignment.CenterHorizontally)
                )

                // Header section
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 20.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    IconButton(onClick = { onDismiss() }) {
                        Icon(imageVector = Icons.Default.Close, contentDescription = "Close", tint = TextPrimary)
                    }
                    Text(
                        text = "您的餐食",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary
                    )
                    IconButton(onClick = {
                        Toast.makeText(context, "您的餐食链接已复制，去分享吧！", Toast.LENGTH_SHORT).show()
                    }) {
                        Icon(imageVector = Icons.Default.Share, contentDescription = "Share", tint = TextPrimary)
                    }
                }

                // Scrollable details column
                Column(
                    modifier = Modifier
                        .weight(1f)
                        .verticalScroll(rememberScrollState())
                        .padding(horizontal = 20.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // Time and type banner row
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .clip(RoundedCornerShape(8.dp))
                                    .background(AccentOrange.copy(alpha = 0.2f))
                                    .padding(horizontal = 8.dp, vertical = 4.dp)
                            ) {
                                Text(text = meal.mealType, color = AccentOrange, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                            }
                            Spacer(modifier = Modifier.width(8.dp))
                            Text(
                                text = "📅 ${meal.dateString} 周五 🕒 下午 ${meal.timeString}",
                                color = TextSecondary,
                                fontSize = 12.sp
                            )
                        }

                        // Collection Heart
                        IconButton(onClick = { viewModel.toggleReviewedCollection() }) {
                            Icon(
                                imageVector = if (reviewedIsCollected) Icons.Default.Favorite else Icons.Default.FavoriteBorder,
                                contentDescription = "Favorite",
                                tint = if (reviewedIsCollected) AccentOrange else TextSecondary
                            )
                        }
                    }

                    // --- Nutrient progress tracks (Screen 1 core box) ---
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .border(1.dp, Color.White.copy(alpha = 0.05f), RoundedCornerShape(16.dp)),
                        colors = CardDefaults.cardColors(containerColor = CardSurface)
                    ) {
                        Column(
                            modifier = Modifier.padding(16.dp),
                            verticalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            // Overall scale multiplier info
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.Bottom
                            ) {
                                Text(
                                    text = "$scaledCalories 千卡",
                                    fontSize = 24.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = TextPrimary
                                )
                                Text(
                                    text = "总计卡路里",
                                    fontSize = 12.sp,
                                    color = TextSecondary
                                )
                            }
                            // Calorie full line
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(8.dp)
                                    .clip(CircleShape)
                                    .background(Color.White.copy(alpha = 0.06f))
                            ) {
                                Box(
                                    modifier = Modifier
                                        .fillMaxHeight()
                                        .fillMaxWidth(0.6f) // static mock level for looks
                                        .clip(CircleShape)
                                        .background(AccentOrange)
                                )
                            }

                            Spacer(modifier = Modifier.height(2.dp))

                            // Protein progress bar
                            HorizontalMacroBar(
                                label = "蛋白质",
                                amountString = "${scaledProtein}克",
                                fraction = 0.45f,
                                color = AccentTeal
                            )

                            // Carbohydrate progress bar
                            HorizontalMacroBar(
                                label = "碳水化合物",
                                amountString = "${scaledCarbs}克",
                                fraction = 0.55f,
                                color = AccentPurple
                            )

                            // Fat progress bar
                            HorizontalMacroBar(
                                label = "脂肪",
                                amountString = "${scaledFat}克",
                                fraction = 0.25f,
                                color = AccentYellow
                            )
                        }
                    }

                    // --- Food Breakdown List ---
                    Text(
                        text = "包含食物",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = TextPrimary,
                        modifier = Modifier.padding(top = 8.dp)
                    )

                    // Card block containing item list and alternative recommendations
                    reviewedItems.forEach { item ->
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .border(1.dp, Color.White.copy(alpha = 0.03f), RoundedCornerShape(14.dp)),
                            colors = CardDefaults.cardColors(containerColor = CardSurface)
                        ) {
                            Column(
                                modifier = Modifier.padding(14.dp),
                                verticalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Column {
                                        Text(text = item.name, color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                                        Text(
                                            text = "${(item.calories * scaleFactor).toInt()} 千卡 / ${item.weightString}",
                                            color = TextSecondary,
                                            fontSize = 12.sp,
                                            modifier = Modifier.padding(top = 2.dp)
                                        )
                                    }
                                    IconButton(
                                        onClick = { /* Edit item */ },
                                        modifier = Modifier.size(32.dp)
                                    ) {
                                        Icon(imageVector = Icons.Default.Edit, contentDescription = "Edit flag", tint = AccentTeal, modifier = Modifier.size(16.dp))
                                    }
                                }

                                // Alternative suggestion box
                                if (item.alternatives.isNotEmpty()) {
                                    Column(
                                        verticalArrangement = Arrangement.spacedBy(4.dp)
                                    ) {
                                        Text(text = "可能也是 / 健康替代:", color = TextSecondary.copy(alpha = 0.8f), fontSize = 11.sp)
                                        FlowRow(
                                            horizontalArrangement = Arrangement.spacedBy(6.dp),
                                            verticalArrangement = Arrangement.spacedBy(6.dp)
                                        ) {
                                            item.alternatives.forEach { alt ->
                                                Box(
                                                    modifier = Modifier
                                                        .clip(RoundedCornerShape(8.dp))
                                                        .background(Color.White.copy(alpha = 0.05f))
                                                        .border(0.5.dp, AccentTeal.copy(alpha = 0.3f), RoundedCornerShape(8.dp))
                                                        .clickable {
                                                            // Exchange food with alternative selection!
                                                            viewModel.addMissingFoodItem(alt, item.calories, "1 份")
                                                            Toast.makeText(context, "已为您替换为健康选择: $alt", Toast.LENGTH_SHORT).show()
                                                        }
                                                        .padding(horizontal = 8.dp, vertical = 4.dp)
                                                ) {
                                                    Text(text = "$alt +", color = AccentTeal, fontSize = 11.sp)
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    // --- Portion scaling slider (`- 1 +`) ---
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(52.dp)
                            .clip(RoundedCornerShape(14.dp))
                            .background(CardSurface)
                            .padding(horizontal = 16.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text(text = "份数倍数 (Portions):", color = TextPrimary, fontSize = 13.sp, fontWeight = FontWeight.Medium)
                        Row(
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            IconButton(
                                onClick = { viewModel.changePortion(-1) },
                                modifier = Modifier
                                    .size(34.dp)
                                    .clip(CircleShape)
                                    .background(Color.White.copy(alpha = 0.08f))
                            ) {
                                Icon(imageVector = Icons.Default.Remove, contentDescription = "decrease", tint = TextPrimary, modifier = Modifier.size(16.dp))
                            }
                            Spacer(modifier = Modifier.width(16.dp))
                            Text(
                                text = "$portionScale",
                                color = TextPrimary,
                                fontWeight = FontWeight.Bold,
                                fontSize = 16.sp
                            )
                            Spacer(modifier = Modifier.width(16.dp))
                            IconButton(
                                onClick = { viewModel.changePortion(1) },
                                modifier = Modifier
                                    .size(34.dp)
                                    .clip(CircleShape)
                                    .background(Color.White.copy(alpha = 0.08f))
                            ) {
                                Icon(imageVector = Icons.Default.Add, contentDescription = "increase", tint = TextPrimary, modifier = Modifier.size(16.dp))
                            }
                        }
                    }

                    // --- Add custom missing food item ---
                    Button(
                        onClick = { showAddFoodDialog = true },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(48.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Color.Transparent),
                        border = BorderStroke(1.dp, AccentTeal),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Icon(imageVector = Icons.Default.Add, contentDescription = "add", tint = AccentTeal, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(text = "添加缺失的食物", color = AccentTeal, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                    }

                    // --- NutriAI Rating B banner panel ---
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .border(1.dp, AccentTeal.copy(alpha = 0.15f), RoundedCornerShape(16.dp)),
                        colors = CardDefaults.cardColors(containerColor = CardSurface)
                    ) {
                        Row(
                            modifier = Modifier.padding(16.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(44.dp)
                                    .clip(RoundedCornerShape(10.dp))
                                    .background(AccentOrange),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(text = meal.healthScore, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 20.sp)
                            }
                            Spacer(modifier = Modifier.width(16.dp))
                            Column {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(imageVector = Icons.Default.CheckCircle, contentDescription = "ok", tint = AccentTeal, modifier = Modifier.size(14.dp))
                                    Spacer(modifier = Modifier.width(4.dp))
                                    Text(text = "审核评级良好", color = AccentTeal, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                                }
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = meal.healthMessage + "\nNutriAI 智能追踪健康指数评分系统",
                                    color = TextSecondary,
                                    fontSize = 11.sp,
                                    lineHeight = 15.sp
                                )
                            }
                        }
                    }

                    // --- Foldable Key Micronutrients ---
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .border(0.5.dp, Color.White.copy(alpha = 0.04f), RoundedCornerShape(12.dp)),
                        colors = CardDefaults.cardColors(containerColor = CardSurface)
                    ) {
                        Column {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clickable { keyMicrosExpanded = !keyMicrosExpanded }
                                    .padding(horizontal = 16.dp, vertical = 12.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Icon(imageVector = Icons.Default.Equalizer, contentDescription = "micros", tint = AccentTeal, modifier = Modifier.size(16.dp))
                                    Spacer(modifier = Modifier.width(10.dp))
                                    Text(text = "关键微量营养素", color = TextPrimary, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                                }
                                Icon(
                                    imageVector = if (keyMicrosExpanded) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                                    tint = TextSecondary,
                                    contentDescription = "Expand"
                                )
                            }

                            if (keyMicrosExpanded) {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(start = 16.dp, end = 16.dp, bottom = 16.dp),
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    MicronutrientLabel("维生素 D", "85%", AccentTeal)
                                    MicronutrientLabel("铁 (Fe)", "42%", AccentPurple)
                                    MicronutrientLabel("膳食纤维", "74%", AccentYellow)
                                    MicronutrientLabel("钠 (Na)", "安全值", AccentTeal)
                                }
                            }
                        }
                    }

                    // --- Notes text field ---
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .border(0.5.dp, Color.White.copy(alpha = 0.04f), RoundedCornerShape(12.dp)),
                        colors = CardDefaults.cardColors(containerColor = CardSurface)
                    ) {
                        Column(modifier = Modifier.padding(14.dp)) {
                            Text(text = "📝 晚餐餐食备注", color = TextPrimary, fontSize = 13.sp, fontWeight = FontWeight.Bold)
                            Spacer(modifier = Modifier.height(10.dp))
                            OutlinedTextField(
                                value = reviewedNotes,
                                onValueChange = { if (it.length <= 500) viewModel.updateReviewedNotes(it) },
                                placeholder = { Text("添加关于此餐的备注...", fontSize = 13.sp) },
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(110.dp),
                                shape = RoundedCornerShape(12.dp),
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedBorderColor = AccentTeal,
                                    unfocusedBorderColor = Color.White.copy(alpha = 0.08f),
                                    unfocusedPlaceholderColor = TextSecondary.copy(alpha = 0.5f),
                                    focusedPlaceholderColor = TextSecondary.copy(alpha = 0.5f)
                                )
                            )
                            Spacer(modifier = Modifier.height(6.dp))
                            Text(
                                text = "${reviewedNotes.length}/500",
                                color = TextSecondary,
                                fontSize = 10.sp,
                                modifier = Modifier.align(Alignment.End)
                            )
                        }
                    }

                    // --- Satisfaction Rating ---
                    Column(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(text = "您的结果如何 / 该餐口感如何?", color = TextSecondary, fontSize = 12.sp)
                        Spacer(modifier = Modifier.height(10.dp))
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(16.dp)
                        ) {
                            // Thumbs down
                            IconButton(
                                onClick = { viewModel.setReviewedLiked(false) },
                                modifier = Modifier
                                    .size(46.dp)
                                    .clip(CircleShape)
                                    .background(if (reviewedIsLiked == false) AccentOrange else Color.White.copy(alpha = 0.08f))
                            ) {
                                Icon(imageVector = Icons.Default.ThumbDown, contentDescription = "dislike", tint = if (reviewedIsLiked == false) Color.Black else TextPrimary)
                            }

                            // Thumbs up
                            IconButton(
                                onClick = { viewModel.setReviewedLiked(true) },
                                modifier = Modifier
                                    .size(46.dp)
                                    .clip(CircleShape)
                                    .background(if (reviewedIsLiked == true) AccentTeal else Color.White.copy(alpha = 0.08f))
                            ) {
                                Icon(imageVector = Icons.Default.ThumbUp, contentDescription = "like", tint = if (reviewedIsLiked == true) Color.Black else TextPrimary)
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(16.dp))
                }

                // Bottom CTA action bar
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(20.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Button(
                        onClick = { viewModel.deleteMeal(meal) },
                        modifier = Modifier
                            .weight(0.4f)
                            .height(54.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = Color.White.copy(alpha = 0.08f)),
                        shape = RoundedCornerShape(14.dp)
                    ) {
                        Text("删除", color = Color.Red, fontWeight = FontWeight.Bold)
                    }

                    Button(
                        onClick = { viewModel.saveReviewedMeal() },
                        modifier = Modifier
                            .weight(1f)
                            .height(54.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = AccentOrange),
                        shape = RoundedCornerShape(14.dp)
                    ) {
                        Text("保存餐食", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 16.sp)
                    }
                }
            }
        }
    }

    // Modal adding missing custom meal item dialog
    if (showAddFoodDialog) {
        AddFoodItemDialog(
            onDismiss = { showAddFoodDialog = false },
            onAdd = { name, calories, grams ->
                viewModel.addMissingFoodItem(name, calories, "${grams}克")
                showAddFoodDialog = false
            }
        )
    }
}

@Composable
fun HorizontalMacroBar(label: String, amountString: String, fraction: Float, color: Color) {
    Column(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(text = amountString, color = TextPrimary, fontWeight = FontWeight.Bold, fontSize = 14.sp)
            Text(text = label, color = TextSecondary, fontSize = 11.sp)
        }
        Spacer(modifier = Modifier.height(4.dp))
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(4.dp)
                .clip(CircleShape)
                .background(Color.White.copy(alpha = 0.06f))
        ) {
            Box(
                modifier = Modifier
                    .fillMaxHeight()
                    .fillMaxWidth(fraction)
                    .clip(CircleShape)
                    .background(color)
            )
        }
    }
}

@Composable
fun MicronutrientLabel(title: String, score: String, color: Color) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Box(
            modifier = Modifier
                .size(6.dp)
                .clip(CircleShape)
                .background(color)
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(text = title, color = TextSecondary, fontSize = 10.sp)
        Text(text = score, color = TextPrimary, fontSize = 11.sp, fontWeight = FontWeight.Bold)
    }
}

// Dialog: Add custom missing food item dialog
@Composable
fun AddFoodItemDialog(onDismiss: () -> Unit, onAdd: (String, Int, Int) -> Unit) {
    var name by remember { mutableStateOf("") }
    var calories by remember { mutableStateOf("") }
    var grams by remember { mutableStateOf("") }

    Dialog(onDismissRequest = onDismiss) {
        Card(
            colors = CardDefaults.cardColors(containerColor = CardSurface),
            shape = RoundedCornerShape(16.dp),
            modifier = Modifier
                .fillMaxWidth()
                .border(1.dp, Color.White.copy(alpha = 0.08f), RoundedCornerShape(16.dp))
        ) {
            Column(
                modifier = Modifier.padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                Text("添加缺失的食物", color = TextPrimary, fontSize = 16.sp, fontWeight = FontWeight.Bold)

                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("食材名称如: 香松") },
                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = AccentTeal)
                )

                OutlinedTextField(
                    value = calories,
                    onValueChange = { calories = it },
                    label = { Text("对应热量 (千卡)") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = AccentTeal)
                )

                OutlinedTextField(
                    value = grams,
                    onValueChange = { grams = it },
                    label = { Text("大约克数 (克/g)") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = AccentTeal)
                )

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.End,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    TextButton(onClick = onDismiss) {
                        Text("取消", color = TextSecondary)
                    }
                    Spacer(modifier = Modifier.width(12.dp))
                    Button(
                        onClick = {
                            val calValue = calories.toIntOrNull() ?: 50
                            val gramValue = grams.toIntOrNull() ?: 50
                            if (name.isNotEmpty()) {
                                onAdd(name, calValue, gramValue)
                            }
                        },
                        colors = ButtonDefaults.buttonColors(containerColor = AccentOrange)
                    ) {
                        Text("确定添加")
                    }
                }
            }
        }
    }
}

// Dialog: AI Parser dialog
@Composable
fun AiAnalyzeDialog(
    isAnalyzing: Boolean,
    onDismiss: () -> Unit,
    onAnalyze: (String) -> Unit
) {
    var textInput by remember { mutableStateOf("") }
    var isRecording by remember { mutableStateOf(false) }

    // Wave pulsator for recorder simulation
    val infiniteTransition = rememberInfiniteTransition(label = "VoicePulse")
    val pulseScale1 by infiniteTransition.animateFloat(
        initialValue = 1.0f,
        targetValue = 1.6f,
        animationSpec = infiniteRepeatable(
            animation = tween(1200, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "Pulse1"
    )
    val pulseAlpha1 by infiniteTransition.animateFloat(
        initialValue = 0.6f,
        targetValue = 0.0f,
        animationSpec = infiniteRepeatable(
            animation = tween(1200, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "Alpha1"
    )

    Dialog(onDismissRequest = onDismiss) {
        Card(
            colors = CardDefaults.cardColors(containerColor = CardSurface),
            shape = RoundedCornerShape(24.dp),
            modifier = Modifier
                .fillMaxWidth()
                .border(1.dp, Color.White.copy(alpha = 0.08f), RoundedCornerShape(24.dp))
        ) {
            Column(
                modifier = Modifier.padding(24.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "AI 语音与文字智能识别",
                        color = TextPrimary,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold
                    )
                    if (isAnalyzing) {
                        CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.5.dp, color = AccentTeal)
                    }
                }

                Text(
                    text = "说出或者输入您吃了什么菜品，智能 AI 将为您彻底拆分营养素和估算精确卡路里。",
                    color = TextSecondary,
                    fontSize = 12.sp,
                    lineHeight = 16.sp,
                    modifier = Modifier.align(Alignment.Start)
                )

                // Simulated Glowing Oscilloscope / Mic Button Box
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(130.dp),
                    contentAlignment = Alignment.Center
                ) {
                    if (isRecording) {
                        // Halo wave 1
                        Box(
                            modifier = Modifier
                                .size(72.dp)
                                .graphicsLayer {
                                    scaleX = pulseScale1
                                    scaleY = pulseScale1
                                    alpha = pulseAlpha1
                                }
                                .clip(CircleShape)
                                .background(AccentOrange)
                        )
                        LaunchedEffect(Unit) {
                            // Typing simulation of spoken text
                            val spokenText = "我晚餐吃了一盘烤鸡胸肉，搭配白米饭和一盘精美的炒青菜"
                            textInput = ""
                            spokenText.forEachIndexed { index, char ->
                                kotlinx.coroutines.delay(80)
                                textInput += char
                            }
                            isRecording = false
                        }
                    }

                    // Circle Mic button
                    Box(
                        modifier = Modifier
                            .size(72.dp)
                            .clip(CircleShape)
                            .background(if (isRecording) AccentOrange else Color.White.copy(alpha = 0.05f))
                            .border(2.dp, AccentOrange, CircleShape)
                            .clickable {
                                isRecording = !isRecording
                            },
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = if (isRecording) Icons.Default.MicNone else Icons.Default.Mic,
                            contentDescription = "Simulated record mic",
                            tint = if (isRecording) Color.White else AccentOrange,
                            modifier = Modifier.size(32.dp)
                        )
                    }

                    Text(
                        text = if (isRecording) "🎤 聆听中，正在识别您的语音分贝..." else "点击上方话筒，模拟「语音输入」描述餐食",
                        color = if (isRecording) AccentOrange else TextSecondary,
                        fontSize = 11.sp,
                        modifier = Modifier.align(Alignment.BottomCenter)
                    )
                }

                // TextInput textarea Box
                OutlinedTextField(
                    value = textInput,
                    onValueChange = { textInput = it },
                    placeholder = { Text("可以用语音输入，也可以直接在此处键入餐食。例如：晚餐吃了烤鸡配番茄炒蛋和一碗红薯面条...", fontSize = 13.sp, color = TextSecondary.copy(alpha = 0.5f)) },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(110.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = AccentOrange,
                        unfocusedBorderColor = Color.White.copy(alpha = 0.08f)
                    ),
                    shape = RoundedCornerShape(12.dp)
                )

                // Quick preloaded shortcuts list
                Row(
                    modifier = Modifier.horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(8.dp))
                            .background(Color.White.copy(alpha = 0.05f))
                            .clickable { textInput = "豆腐木耳热汤" }
                            .padding(8.dp)
                    ) {
                        Text("🍲 豆腐木耳热汤", color = AccentTeal, fontSize = 11.sp)
                    }
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(8.dp))
                            .background(Color.White.copy(alpha = 0.05f))
                            .clickable { textInput = "烤鸡, 白米饭, 炒青菜" }
                            .padding(8.dp)
                    ) {
                        Text("🍗 烤鸡米饭套餐", color = AccentYellow, fontSize = 11.sp)
                    }
                    Box(
                        modifier = Modifier
                            .clip(RoundedCornerShape(8.dp))
                            .background(Color.White.copy(alpha = 0.05f))
                            .clickable { textInput = "午餐吃了三文鱼藜麦波奇饭" }
                            .padding(8.dp)
                    ) {
                        Text("🥗 三文鱼波奇饭", color = AccentPurple, fontSize = 11.sp)
                    }
                }

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.End
                ) {
                    TextButton(onClick = onDismiss) {
                        Text("取消", color = TextSecondary)
                    }
                    Spacer(modifier = Modifier.width(12.dp))
                    Button(
                        onClick = { onAnalyze(textInput) },
                        colors = ButtonDefaults.buttonColors(containerColor = AccentOrange),
                        shape = RoundedCornerShape(10.dp),
                        enabled = textInput.isNotEmpty() && !isAnalyzing
                    ) {
                        Text("Gemini 智能识别")
                    }
                }
            }
        }
    }
}

// --- COMMON: CUSTOM BOTTOM NAVIGATION BAR ---

@Composable
fun NutriBottomNavigationBar(
    currentTab: MainTab,
    onTabSelected: (MainTab) -> Unit,
    isOpen: Boolean,
    onAddClick: () -> Unit
) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(84.dp)
            .background(Color.Black.copy(alpha = 0.85f)) // Glassmorphic translucent visual
            .windowInsetsPadding(WindowInsets.navigationBars) // Respect Android Notch & Swipe bar areas
    ) {
        // Active line separation
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(0.5.dp)
                .background(Color.White.copy(alpha = 0.08f))
        )

        Row(
            modifier = Modifier.fillMaxSize(),
            horizontalArrangement = Arrangement.SpaceAround,
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Tab 1: Home
            BottomNavItem(
                icon = Icons.Default.Home,
                label = "首页",
                isSelected = currentTab == MainTab.HOME,
                onClick = { onTabSelected(MainTab.HOME) }
            )

            // Tab 2: Diary
            BottomNavItem(
                icon = Icons.Default.Book,
                label = "日记",
                isSelected = currentTab == MainTab.DIARY,
                onClick = { onTabSelected(MainTab.DIARY) }
            )

            // Central elevated Plus / Close symbol
            Box(
                modifier = Modifier
                    .size(60.dp)
                    .offset(y = (-10).dp)
                    .clip(CircleShape)
                    .background(
                        brush = Brush.radialGradient(
                            colors = listOf(AccentOrange, AccentOrange.copy(alpha = 0.8f))
                        )
                    )
                    .clickable { onAddClick() },
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = if (isOpen) Icons.Default.Close else Icons.Default.Add,
                    contentDescription = if (isOpen) "Close menu" else "Add meal",
                    tint = Color.White,
                    modifier = Modifier.size(32.dp)
                )
            }

            // Tab 3: Analysis
            BottomNavItem(
                icon = Icons.Default.BarChart,
                label = "分析",
                isSelected = currentTab == MainTab.ANALYSIS,
                onClick = { onTabSelected(MainTab.ANALYSIS) }
            )

            // Tab 4: Profile
            BottomNavItem(
                icon = Icons.Default.Person,
                label = "我的",
                isSelected = currentTab == MainTab.PROFILE,
                onClick = { onTabSelected(MainTab.PROFILE) }
            )
        }
    }
}

// --- NEW STYLISH COMMODITIES: QUICK LOG PILL & DIALOG OVERLAYS ---

@Composable
fun QuickLogPill(
    remainingCalories: Int,
    onSearchClick: () -> Unit,
    onCameraClick: () -> Unit,
    onVoiceClick: () -> Unit
) {
    Card(
        shape = RoundedCornerShape(28.dp),
        colors = CardDefaults.cardColors(containerColor = AccentOrange),
        modifier = Modifier
            .fillMaxWidth()
            .height(84.dp)
            .border(1.dp, Color.White.copy(alpha = 0.2f), RoundedCornerShape(28.dp)),
        elevation = CardDefaults.cardElevation(defaultElevation = 8.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 24.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            // Left Text Section
            Column(
                modifier = Modifier.weight(1f),
                verticalArrangement = Arrangement.Center
            ) {
                Text(
                    text = "Log Food",
                    style = TextStyle(
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White,
                        letterSpacing = 0.15.sp
                    )
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = "$remainingCalories kcal remaining",
                    style = TextStyle(
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Medium,
                        color = Color.White.copy(alpha = 0.85f)
                    )
                )
            }

            // Right Circular Quick Access Actions Row
            Row(
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Button 1: Search
                QuickLogPillActionButton(
                    icon = Icons.Default.Search,
                    contentDescription = "Search previous food",
                    onClick = onSearchClick
                )

                // Button 2: Camera
                QuickLogPillActionButton(
                    icon = Icons.Default.PhotoCamera,
                    contentDescription = "Camera scanner",
                    onClick = onCameraClick
                )

                // Button 3: Mic
                QuickLogPillActionButton(
                    icon = Icons.Default.Mic,
                    contentDescription = "Voice dictation",
                    onClick = onVoiceClick
                )
            }
        }
    }
}

@Composable
fun QuickLogPillActionButton(
    icon: ImageVector,
    contentDescription: String,
    onClick: () -> Unit
) {
    // Slightly darker orange for high-contrast circular action button to match screenshot style
    val buttonColor = Color(0xFFC2410C)
    Box(
        modifier = Modifier
            .size(46.dp)
            .clip(CircleShape)
            .background(buttonColor)
            .clickable { onClick() },
        contentAlignment = Alignment.Center
    ) {
        Icon(
            imageVector = icon,
            contentDescription = contentDescription,
            tint = Color.White,
            modifier = Modifier.size(24.dp)
        )
    }
}

@Composable
fun SearchFoodDialog(
    loggedMeals: List<Meal>,
    onDismiss: () -> Unit,
    onSelectMeal: (Meal) -> Unit
) {
    var searchQuery by remember { mutableStateOf("") }
    
    // Some popular standard presets always available to search
    val standardPresets = listOf(
        Meal(
            id = UUID.randomUUID().toString(),
            title = "精选牛油果大虾轻食沙拉",
            mealType = "午餐",
            dateString = "",
            timeString = "12:00",
            calories = 340,
            protein = 24,
            carbs = 18,
            fat = 15,
            notes = "清新低糖脂，蛋白质矿物质十分丰富！",
            imageUrl = "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=500&auto=format&fit=crop&q=60",
            multiplier = 1.0,
            isCollected = true,
            isLiked = true,
            healthScore = "A",
            healthMessage = "极佳的减脂高蛋白选择",
            itemsJson = "[]"
        ),
        Meal(
            id = UUID.randomUUID().toString(),
            title = "香煎安格斯慢烤西冷牛排",
            mealType = "晚餐",
            dateString = "",
            timeString = "19:00",
            calories = 480,
            protein = 38,
            carbs = 5,
            fat = 28,
            notes = "香气四溢，纯正动物蛋白铁质来源。",
            imageUrl = "https://images.unsplash.com/photo-1432139555190-58524dae6a55?w=500&auto=format&fit=crop&q=60",
            multiplier = 1.0,
            isCollected = false,
            isLiked = null,
            healthScore = "A",
            healthMessage = "高优质蛋白，红肉可适度补充",
            itemsJson = "[]"
        ),
        Meal(
            id = UUID.randomUUID().toString(),
            title = "全麦无糖高纤燕麦包",
            mealType = "早餐",
            dateString = "",
            timeString = "08:30",
            calories = 195,
            protein = 8,
            carbs = 36,
            fat = 3,
            notes = "低升糖优质碳水，饱腹感非常久。",
            imageUrl = "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=500&auto=format&fit=crop&q=60",
            multiplier = 1.0,
            isCollected = true,
            isLiked = true,
            healthScore = "A",
            healthMessage = "优秀的早餐粗粮膳食纤维",
            itemsJson = "[]"
        )
    )

    // Combine user-logged meals and standard presets
    val allUniqueMeals = remember(loggedMeals) {
        val unique = mutableMapOf<String, Meal>()
        standardPresets.forEach { unique[it.title] = it }
        loggedMeals.forEach { unique[it.title] = it }
        unique.values.toList()
    }

    val filteredMeals = allUniqueMeals.filter {
        it.title.contains(searchQuery, ignoreCase = true) ||
        it.mealType.contains(searchQuery, ignoreCase = true)
    }

    Dialog(onDismissRequest = onDismiss) {
        Card(
            colors = CardDefaults.cardColors(containerColor = CardSurface),
            shape = RoundedCornerShape(24.dp),
            modifier = Modifier
                .fillMaxWidth()
                .height(480.dp)
                .border(1.dp, Color.White.copy(alpha = 0.08f), RoundedCornerShape(24.dp))
        ) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(20.dp)
            ) {
                Text(
                    text = "快速搜索食用记录",
                    color = TextPrimary,
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold
                )
                Spacer(modifier = Modifier.height(12.dp))
                
                // Search bar
                OutlinedTextField(
                    value = searchQuery,
                    onValueChange = { searchQuery = it },
                    placeholder = { Text("搜索您曾经记录或吃过的菜品...", fontSize = 13.sp, color = TextSecondary.copy(alpha = 0.6f)) },
                    modifier = Modifier.fillMaxWidth(),
                    leadingIcon = { Icon(imageVector = Icons.Default.Search, contentDescription = "Search icon", tint = TextSecondary) },
                    trailingIcon = {
                        if (searchQuery.isNotEmpty()) {
                            IconButton(onClick = { searchQuery = "" }) {
                                Icon(imageVector = Icons.Default.Close, contentDescription = "Clear", tint = TextSecondary)
                            }
                        }
                    },
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = AccentOrange,
                        unfocusedBorderColor = Color.White.copy(alpha = 0.08f)
                    ),
                    shape = RoundedCornerShape(12.dp),
                    singleLine = true
                )
                
                Spacer(modifier = Modifier.height(16.dp))
                
                Text(
                    text = "共有 ${filteredMeals.size} 个菜品符合条件",
                    color = TextSecondary,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold
                )
                Spacer(modifier = Modifier.height(10.dp))
                
                // Meal List
                LazyColumn(
                    modifier = Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    if (filteredMeals.isEmpty()) {
                        item {
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(top = 40.dp),
                                contentAlignment = Alignment.Center
                            ) {
                                Text("没有找到匹配的吃过菜品", color = TextSecondary, fontSize = 13.sp)
                            }
                        }
                    } else {
                        items(filteredMeals) { meal ->
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clip(RoundedCornerShape(12.dp))
                                    .background(Color.White.copy(alpha = 0.03f))
                                    .clickable { onSelectMeal(meal) }
                                    .padding(10.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                // Thumbnail
                                Box(
                                    modifier = Modifier
                                        .size(44.dp)
                                        .clip(RoundedCornerShape(8.dp))
                                        .background(Color.White.copy(alpha = 0.05f))
                                ) {
                                    if (meal.imageUrl != null) {
                                        AsyncImage(
                                            model = meal.imageUrl,
                                            contentDescription = meal.title,
                                            contentScale = ContentScale.Crop,
                                            modifier = Modifier.fillMaxSize()
                                        )
                                    } else {
                                        Icon(
                                            imageVector = Icons.Default.Restaurant,
                                            contentDescription = null,
                                            tint = TextSecondary,
                                            modifier = Modifier.align(Alignment.Center)
                                        )
                                    }
                                }
                                
                                Spacer(modifier = Modifier.width(12.dp))
                                
                                // Details
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        text = meal.title,
                                        color = TextPrimary,
                                        fontSize = 14.sp,
                                        fontWeight = FontWeight.Bold,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis
                                    )
                                    Spacer(modifier = Modifier.height(2.dp))
                                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                        Text(text = "${meal.calories} kcal", color = AccentOrange, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                                        Text(text = "℗ ${meal.protein}g", color = AccentTeal, fontSize = 11.sp)
                                        Text(text = "© ${meal.carbs}g", color = AccentPurple, fontSize = 11.sp)
                                    }
                                }
                                
                                Icon(
                                    imageVector = Icons.Default.AddCircle,
                                    contentDescription = "Quick add",
                                    tint = AccentOrange,
                                    modifier = Modifier.size(24.dp)
                                )
                            }
                        }
                    }
                }
                
                Spacer(modifier = Modifier.height(10.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.End
                ) {
                    TextButton(onClick = onDismiss) {
                        Text("关闭", color = TextSecondary)
                    }
                }
            }
        }
    }
}

@Composable
fun CameraSimulationDialog(
    onDismiss: () -> Unit,
    onSuccessAdd: (Meal) -> Unit
) {
    var isCapturing by remember { mutableStateOf(false) }
    var captureComplete by remember { mutableStateOf(false) }
    var isAnalyzing by remember { mutableStateOf(false) }
    
    // Choose a random fancy healthy meal to simulate scanning
    val simulatedMeals = listOf(
        Meal(
            id = UUID.randomUUID().toString(),
            title = "全麦低GI牛油果流心煎蛋多士",
            mealType = "早餐",
            dateString = "", 
            timeString = "08:15",
            calories = 312,
            protein = 16,
            carbs = 28,
            fat = 12,
            notes = "拍照自动生成。轻油牛油果泥搭配多谷物全麦，温和饱腹。",
            imageUrl = "https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=500&auto=format&fit=crop&q=60",
            multiplier = 1.0,
            isCollected = false,
            isLiked = null,
            healthScore = "A",
            healthMessage = "极佳的清晨优质脂肪与膳食纤维摄入",
            itemsJson = "[]"
        ),
        Meal(
            id = UUID.randomUUID().toString(),
            title = "炭烤安格斯瘦牛肉配紫薯沙拉",
            mealType = "午餐",
            dateString = "",
            timeString = "12:30",
            calories = 520,
            protein = 44,
            carbs = 35,
            fat = 18,
            notes = "拍照自动生成。安格斯瘦牛肉搭配软糯减脂紫薯，双重饱腹。",
            imageUrl = "https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=500&auto=format&fit=crop&q=60",
            multiplier = 1.0,
            isCollected = false,
            isLiked = true,
            healthScore = "A",
            healthMessage = "优质高蛋白饱腹组合，有助于肌肉合成",
            itemsJson = "[]"
        ),
        Meal(
            id = UUID.randomUUID().toString(),
            title = "低卡烟熏三文鱼藜麦轻卡波奇饭",
            mealType = "晚餐",
            dateString = "",
            timeString = "18:30",
            calories = 410,
            protein = 28,
            carbs = 42,
            fat = 14,
            notes = "拍照自动生成。新鲜烟熏三文鱼、藜麦加爽脆圣女果，极佳的轻食餐。",
            imageUrl = "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=500&auto=format&fit=crop&q=60",
            multiplier = 1.0,
            isCollected = true,
            isLiked = true,
            healthScore = "A",
            healthMessage = "Omega-3不饱和脂肪酸极其丰富，清爽无负担",
            itemsJson = "[]"
        )
    )
    
    val selectedSimulatedMeal = remember { simulatedMeals.random() }

    // Floating Scanner laser animation
    val infiniteTransition = rememberInfiniteTransition(label = "Laser")
    val laserYPercent by infiniteTransition.animateFloat(
        initialValue = 0.1f,
        targetValue = 0.9f,
        animationSpec = infiniteRepeatable(
            animation = tween(1500, easing = LinearEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "LaserY"
    )

    Dialog(onDismissRequest = onDismiss) {
        Card(
            colors = CardDefaults.cardColors(containerColor = Color.Black),
            shape = RoundedCornerShape(24.dp),
            modifier = Modifier
                .fillMaxWidth()
                .height(480.dp)
                .border(2.dp, AccentOrange, RoundedCornerShape(24.dp))
        ) {
            Box(modifier = Modifier.fillMaxSize()) {
                if (!captureComplete) {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(16.dp)
                    ) {
                        // Background food preview image
                        AsyncImage(
                            model = selectedSimulatedMeal.imageUrl,
                            contentDescription = "Simulated viewfinder background",
                            contentScale = ContentScale.Crop,
                            modifier = Modifier
                                .fillMaxSize()
                                .clip(RoundedCornerShape(16.dp))
                        )

                        // Reticle Corners / Camera Box guides
                        Canvas(modifier = Modifier.fillMaxSize()) {
                            val w = size.width
                            val h = size.height
                            val cornerSize = 30.dp.toPx()
                            val lineThickness = 3.dp.toPx()
                            
                            // Top left
                            drawRect(color = AccentOrange, topLeft = Offset(0f, 0f), size = Size(cornerSize, lineThickness))
                            drawRect(color = AccentOrange, topLeft = Offset(0f, 0f), size = Size(lineThickness, cornerSize))
                            // Top right
                            drawRect(color = AccentOrange, topLeft = Offset(w - cornerSize, 0f), size = Size(cornerSize, lineThickness))
                            drawRect(color = AccentOrange, topLeft = Offset(w - lineThickness, 0f), size = Size(lineThickness, cornerSize))
                            // Bottom left
                            drawRect(color = AccentOrange, topLeft = Offset(0f, h - lineThickness), size = Size(cornerSize, lineThickness))
                            drawRect(color = AccentOrange, topLeft = Offset(0f, h - cornerSize), size = Size(lineThickness, cornerSize))
                            // Bottom right
                            drawRect(color = AccentOrange, topLeft = Offset(w - cornerSize, h - lineThickness), size = Size(cornerSize, lineThickness))
                            drawRect(color = AccentOrange, topLeft = Offset(w - lineThickness, h - cornerSize), size = Size(lineThickness, cornerSize))
                        }

                        // Scanning Laser Line Overlay
                        Box(
                            modifier = Modifier
                                .fillMaxWidth()
                                .fillMaxHeight(0.04f)
                                .align(Alignment.TopCenter)
                                .offset(y = 350.dp * laserYPercent)
                                .background(
                                    Brush.verticalGradient(
                                        colors = listOf(Color.Transparent, AccentOrange, Color.Transparent)
                                    )
                                )
                        )

                        // Top indicator banner
                        Box(
                            modifier = Modifier
                                .align(Alignment.TopCenter)
                                .padding(top = 16.dp)
                                .clip(RoundedCornerShape(20.dp))
                                .background(Color.Black.copy(alpha = 0.6f))
                                .padding(horizontal = 14.dp, vertical = 6.dp)
                        ) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Box(modifier = Modifier.size(8.dp).clip(CircleShape).background(Color.Red))
                                Spacer(modifier = Modifier.width(6.dp))
                                Text("REC MOCK CAMERA LIVE", color = Color.White, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                            }
                        }

                        // Footer shutter indicators
                        Column(
                            modifier = Modifier
                                .align(Alignment.BottomCenter)
                                .padding(bottom = 16.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            Text("对准盘中餐食，点击快门自动识别卡路里", color = Color.White, fontSize = 11.sp, fontWeight = FontWeight.SemiBold, modifier = Modifier.background(Color.Black.copy(alpha = 0.6f)).padding(horizontal = 8.dp, vertical = 4.dp).clip(RoundedCornerShape(4.dp)))
                            Spacer(modifier = Modifier.height(12.dp))
                            
                            // Shutter button shape
                            Box(
                                modifier = Modifier
                                    .size(72.dp)
                                    .clip(CircleShape)
                                    .background(Color.White)
                                    .border(4.dp, AccentOrange, CircleShape)
                                    .clickable {
                                        isCapturing = true
                                    },
                                contentAlignment = Alignment.Center
                            ) {
                                Box(
                                    modifier = Modifier
                                        .size(52.dp)
                                        .clip(CircleShape)
                                        .background(AccentOrange)
                                )
                            }
                        }
                    }

                    // Shutter capture flash card effect
                    if (isCapturing) {
                        Box(
                            modifier = Modifier
                                .fillMaxSize()
                                .background(Color.White)
                        )
                        LaunchedEffect(Unit) {
                            kotlinx.coroutines.delay(120)
                            isCapturing = false
                            captureComplete = true
                            isAnalyzing = true
                        }
                    }
                } else if (isAnalyzing) {
                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(24.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.Center
                    ) {
                        CircularProgressIndicator(color = AccentOrange, strokeWidth = 4.dp, modifier = Modifier.size(56.dp))
                        Spacer(modifier = Modifier.height(24.dp))
                        Text(
                            text = "NutriAI 智能图像热量测算中...",
                            style = TextStyle(color = Color.White, fontSize = 16.sp, fontWeight = FontWeight.Bold)
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = "正在评估食物体积、分量并拆解营养成分数值...",
                            style = TextStyle(color = TextSecondary, fontSize = 12.sp, textAlign = TextAlign.Center)
                        )
                        LaunchedEffect(Unit) {
                            kotlinx.coroutines.delay(1800)
                            isAnalyzing = false
                        }
                    }
                } else {
                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(24.dp),
                        verticalArrangement = Arrangement.SpaceBetween,
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Icon(
                                imageVector = Icons.Default.CheckCircle,
                                contentDescription = "Finished scan",
                                tint = AccentTeal,
                                modifier = Modifier.size(48.dp)
                            )
                            Spacer(modifier = Modifier.height(12.dp))
                            Text(
                                "AI 识别餐盘成功！",
                                color = TextPrimary,
                                fontSize = 18.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }

                        // Display guessed card in preview
                        Card(
                            colors = CardDefaults.cardColors(containerColor = CardSurface),
                            modifier = Modifier
                                .fillMaxWidth()
                                .border(1.dp, Color.White.copy(alpha = 0.08f), RoundedCornerShape(16.dp))
                        ) {
                            Row(
                                modifier = Modifier.padding(12.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                AsyncImage(
                                    model = selectedSimulatedMeal.imageUrl,
                                    contentDescription = selectedSimulatedMeal.title,
                                    contentScale = ContentScale.Crop,
                                    modifier = Modifier
                                        .size(64.dp)
                                        .clip(RoundedCornerShape(8.dp))
                                )
                                Spacer(modifier = Modifier.width(12.dp))
                                Column {
                                    Text(selectedSimulatedMeal.title, color = TextPrimary, fontSize = 14.sp, fontWeight = FontWeight.Bold, maxLines = 1, overflow = TextOverflow.Ellipsis)
                                    Spacer(modifier = Modifier.height(4.dp))
                                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                        Text("${selectedSimulatedMeal.calories} kcal", color = AccentOrange, fontSize = 12.sp, fontWeight = FontWeight.Bold)
                                        Text("℗ ${selectedSimulatedMeal.protein}g", color = AccentTeal, fontSize = 11.sp)
                                        Text("© ${selectedSimulatedMeal.carbs}g", color = AccentPurple, fontSize = 11.sp)
                                    }
                                }
                            }
                        }

                        // Bottom Choice Actions
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(16.dp)
                        ) {
                            Button(
                                onClick = {
                                    captureComplete = false
                                },
                                modifier = Modifier
                                    .weight(1f)
                                    .height(48.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = Color.White.copy(alpha = 0.1f)),
                                shape = RoundedCornerShape(12.dp)
                            ) {
                                Text("重拍", color = Color.White)
                            }

                            Button(
                                onClick = {
                                    onSuccessAdd(selectedSimulatedMeal)
                                    onDismiss()
                                },
                                modifier = Modifier
                                    .weight(1f)
                                    .height(48.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = AccentOrange),
                                shape = RoundedCornerShape(12.dp)
                            ) {
                                Text("确认添加", color = Color.White, fontWeight = FontWeight.Bold)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun BottomNavItem(
    icon: ImageVector,
    label: String,
    isSelected: Boolean,
    onClick: () -> Unit
) {
    Column(
        modifier = Modifier
            .clip(RoundedCornerShape(12.dp))
            .clickable { onClick() }
            .padding(horizontal = 12.dp, vertical = 6.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(
            imageVector = icon,
            contentDescription = label,
            tint = if (isSelected) AccentOrange else TextSecondary,
            modifier = Modifier.size(22.dp)
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = label,
            color = if (isSelected) AccentOrange else TextSecondary,
            fontSize = 11.sp,
            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal
        )
    }
}
