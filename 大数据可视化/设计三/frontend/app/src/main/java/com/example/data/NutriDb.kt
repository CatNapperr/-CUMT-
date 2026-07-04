package com.example.data

import android.content.Context
import androidx.room.*
import com.squareup.moshi.Moshi
import com.squareup.moshi.Types
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import kotlinx.coroutines.flow.Flow

// --- Data Models ---

data class FoodItem(
    val name: String,
    val calories: Int,
    val weightString: String,
    val alternatives: List<String> = emptyList()
)

@Entity(tableName = "meals")
data class Meal(
    @PrimaryKey val id: String,
    val title: String,
    val mealType: String,
    val mealDate: String = "",            // ISO date "2026-06-01"
    val dateString: String,
    val timeString: String,
    val calories: Int,
    val protein: Int,
    val carbs: Int,
    val fat: Int,
    val notes: String = "",
    val imageUrl: String? = null,
    val imageId: String? = null,
    val multiplier: Double = 1.0,
    val isCollected: Boolean = false,
    val isLiked: Boolean? = null,
    val healthScore: String = "B",
    val healthMessage: String = "整体营养均衡良好",
    val source: String = "manual_mock",
    val itemsJson: String,                // Serialized List<FoodItem>
)

// --- Type Converters ---

class Converters {
    private val moshi = Moshi.Builder().addLast(KotlinJsonAdapterFactory()).build()
    private val type = Types.newParameterizedType(List::class.java, FoodItem::class.java)
    private val adapter = moshi.adapter<List<FoodItem>>(type)

    @TypeConverter
    fun fromString(value: String): List<FoodItem> {
        return try {
            adapter.fromJson(value) ?: emptyList()
        } catch (e: Exception) {
            emptyList()
        }
    }

    @TypeConverter
    fun fromList(list: List<FoodItem>): String {
        return adapter.toJson(list)
    }
}

// --- DAO ---

@Dao
interface MealDao {
    @Query("SELECT * FROM meals ORDER BY timeString DESC")
    fun getAllMeals(): Flow<List<Meal>>

    @Query("SELECT * FROM meals WHERE mealDate = :date ORDER BY timeString DESC")
    fun getMealsByDate(date: String): Flow<List<Meal>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertMeal(meal: Meal)

    @Query("SELECT * FROM meals WHERE id = :id")
    suspend fun getMealById(id: String): Meal?

    @Query("DELETE FROM meals WHERE id = :id")
    suspend fun deleteMealById(id: String)

    @Query("DELETE FROM meals")
    suspend fun clearAllMeals()
}

// --- Database ---

@Database(entities = [Meal::class], version = 2, exportSchema = false)
@TypeConverters(Converters::class)
abstract class AppDatabase : RoomDatabase() {
    abstract fun mealDao(): MealDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        fun getDatabase(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "nutriai_database"
                )
                    .fallbackToDestructiveMigration()
                    .build()
                INSTANCE = instance
                instance
            }
        }
    }
}

// --- Repository ---

class MealRepository(private val mealDao: MealDao) {
    val allMeals: Flow<List<Meal>> = mealDao.getAllMeals()

    fun getMealsByDate(date: String): Flow<List<Meal>> = mealDao.getMealsByDate(date)

    suspend fun getMealById(id: String): Meal? = mealDao.getMealById(id)

    suspend fun insert(meal: Meal) = mealDao.insertMeal(meal)

    suspend fun deleteById(id: String) = mealDao.deleteMealById(id)

    suspend fun clear() = mealDao.clearAllMeals()
}
