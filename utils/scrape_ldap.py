    #!/usr/bin/env python3
"""
Course Enrollment Scraper for IIT Delhi LDAP Website

This script scrapes course and student enrollment data from the LDAP website
and stores it in an SQLite database.

Usage:
    python scrape_courses.py
"""

import aiohttp
import asyncio
from bs4 import BeautifulSoup
import sqlite3
import logging
import time
from datetime import datetime
from typing import List, Dict, Optional
import ssl

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "https://ldapweb.iitd.ac.in/LDAP/courses/"
DB_NAME = "courses.db"
REQUEST_TIMEOUT = 30
MAX_CONCURRENT_REQUESTS = 20  # Process 20 courses in parallel


class CourseScraper:
    """Async scraper for LDAP course enrollment data"""
    
    def __init__(self, db_name: str = DB_NAME):
        self.db_name = db_name
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database with required tables"""
        logger.info(f"Initializing database: {self.db_name}")
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Create courses table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS courses (
                course_id TEXT PRIMARY KEY,
                course_name TEXT NOT NULL,
                course_url TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create students table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id TEXT NOT NULL,
                student_name TEXT,
                student_id TEXT,
                entry_number TEXT,
                email TEXT,
                department TEXT,
                FOREIGN KEY (course_id) REFERENCES courses(course_id)
            )
        ''')
        
        # Create index for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_course_id 
            ON students(course_id)
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    async def fetch_page(self, session: aiohttp.ClientSession, url: str) -> Optional[BeautifulSoup]:
        """Fetch a page and return BeautifulSoup object"""
        async with self.semaphore:
            try:
                logger.debug(f"Fetching: {url}")
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as response:
                    response.raise_for_status()
                    html = await response.text()
                    return BeautifulSoup(html, 'lxml')
            except asyncio.TimeoutError:
                logger.error(f"Timeout fetching {url}")
                return None
            except aiohttp.ClientError as e:
                logger.error(f"Error fetching {url}: {e}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error fetching {url}: {e}")
                return None
    
    async def get_course_list(self, session: aiohttp.ClientSession) -> List[Dict[str, str]]:
        """
        Scrape the course listing page to get all courses
        
        Returns:
            List of dictionaries containing course_id, course_name, and course_url
        """
        logger.info("Fetching course list...")
        soup = await self.fetch_page(session, BASE_URL)
        
        if not soup:
            logger.error("Failed to fetch course listing page")
            return []
        
        courses = []
        
        # Try multiple common patterns for course listings
        # Pattern 1: Links in a table
        tables = soup.find_all('table')
        for table in tables:
            links = table.find_all('a', href=True)
            for link in links:
                href = link.get('href')
                if href and 'course' in href.lower():
                    course_name = link.get_text(strip=True)
                    # Extract course ID from href or text
                    course_id = self.extract_course_id(href, course_name)
                    if course_id:
                        # Use urljoin equivalent for aiohttp
                        if href.startswith('http'):
                            course_url = href
                        else:
                            course_url = BASE_URL.rstrip('/') + '/' + href.lstrip('/')
                        courses.append({
                            'course_id': course_id,
                            'course_name': course_name,
                            'course_url': course_url
                        })
        
        # Pattern 2: Links in a list
        if not courses:
            lists = soup.find_all(['ul', 'ol'])
            for lst in lists:
                links = lst.find_all('a', href=True)
                for link in links:
                    href = link.get('href')
                    course_name = link.get_text(strip=True)
                    course_id = self.extract_course_id(href, course_name)
                    if course_id:
                        if href.startswith('http'):
                            course_url = href
                        else:
                            course_url = BASE_URL.rstrip('/') + '/' + href.lstrip('/')
                        courses.append({
                            'course_id': course_id,
                            'course_name': course_name,
                            'course_url': course_url
                        })
        
        # Pattern 3: All links on the page (fallback)
        if not courses:
            links = soup.find_all('a', href=True)
            for link in links:
                href = link.get('href')
                # Skip navigation/external links
                if any(skip in href.lower() for skip in ['javascript', 'mailto', '#', 'http://', 'https://']) and 'ldapweb' not in href.lower():
                    continue
                course_name = link.get_text(strip=True)
                if course_name:
                    course_id = self.extract_course_id(href, course_name)
                    if course_id:
                        if href.startswith('http'):
                            course_url = href
                        else:
                            course_url = BASE_URL.rstrip('/') + '/' + href.lstrip('/')
                        courses.append({
                            'course_id': course_id,
                            'course_name': course_name,
                            'course_url': course_url
                        })
        
        logger.info(f"Found {len(courses)} courses")
        
        # Log first few courses for debugging
        if courses:
            logger.info("Sample courses:")
            for course in courses[:3]:
                logger.info(f"  - {course['course_id']}: {course['course_name']}")
        
        return courses
    
    def extract_course_id(self, href: str, text: str) -> Optional[str]:
        """Extract course ID from href or text"""
        import re
        
        # Priority 1: Try to extract from text (e.g., "2501-MCL111" or "2501-MCL111 (some text)")
        # Format: 4 digits, dash, 2-4 letters, 3-4 digits
        match = re.search(r'(\d{4}-[A-Z]{2,4}\d{3,4})', text)
        if match:
            return match.group(1)
        
        # Priority 2: Try old format without semester prefix (e.g., "CS101")
        match = re.search(r'^([A-Z]{2,4}\d{3,4})', text)
        if match:
            return match.group(1)
        
        # Priority 3: Try to extract from href (e.g., /course/2501-MCL111 or course.php?id=2501-MCL111)
        match = re.search(r'[?&/](?:id|course)[=/]([\w-]+)', href)
        if match:
            return match.group(1)
        
        # Priority 4: Use href path component as ID (filename without extension)
        match = re.search(r'/([^/]+?)(?:\.\w+)?$', href)
        if match:
            return match.group(1)
        
        return None
    
    async def get_course_students(self, session: aiohttp.ClientSession, course_url: str) -> List[Dict[str, str]]:
        """
        Scrape a course page to get enrolled students
        
        Args:
            course_url: URL of the course page
            
        Returns:
            List of dictionaries containing student information
        """
        logger.debug(f"Fetching students from: {course_url}")
        soup = await self.fetch_page(session, course_url)
        
        if not soup:
            logger.error(f"Failed to fetch course page: {course_url}")
            return []
        
        students = []
        
        # Try to find student information in tables
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            
            # Skip header row
            for i, row in enumerate(rows[1:], 1):
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 1:
                    # Extract available information from cells
                    student_data = {}
                    
                    # Common patterns for student data
                    for j, cell in enumerate(cells):
                        text = cell.get_text(strip=True)
                        if not text:
                            continue
                        
                        # Try to identify what each column contains
                        if j == 0:
                            student_data['student_name'] = text
                        elif j == 1:
                            student_data['entry_number'] = text
                        elif j == 2:
                            student_data['student_id'] = text
                        elif '@' in text:
                            student_data['email'] = text
                        elif len(text) <= 10 and any(dept in text.upper() for dept in ['CS', 'EE', 'ME', 'CE', 'CH']):
                            student_data['department'] = text
                    
                    if student_data:
                        students.append(student_data)
        
        # Try alternative patterns (e.g., lists)
        if not students:
            lists = soup.find_all(['ul', 'ol'])
            for lst in lists:
                items = lst.find_all('li')
                for item in items:
                    text = item.get_text(strip=True)
                    students.append({
                        'student_name': text,
                        'student_id': None,
                        'entry_number': None
                    })
        
        logger.debug(f"Found {len(students)} students in {course_url}")
        return students
    
    def save_course(self, course: Dict[str, str], students: List[Dict[str, str]]):
        """Save course and student data to database"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            # Insert or update course
            cursor.execute('''
                INSERT OR REPLACE INTO courses (course_id, course_name, course_url, scraped_at)
                VALUES (?, ?, ?, ?)
            ''', (
                course['course_id'],
                course['course_name'],
                course['course_url'],
                datetime.now()
            ))
            
            # Delete existing students for this course
            cursor.execute('DELETE FROM students WHERE course_id = ?', (course['course_id'],))
            
            # Insert students
            for student in students:
                cursor.execute('''
                    INSERT INTO students (course_id, student_name, student_id, entry_number, email, department)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    course['course_id'],
                    student.get('student_name'),
                    student.get('student_id'),
                    student.get('entry_number'),
                    student.get('email'),
                    student.get('department')
                ))
            
            conn.commit()
            logger.debug(f"Saved course {course['course_id']} with {len(students)} students")
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    async def process_course(self, session: aiohttp.ClientSession, course: Dict[str, str], index: int, total: int) -> int:
        """Process a single course: fetch students and save to database"""
        logger.info(f"Processing course {index}/{total}: {course['course_id']}")
        
        # Get students for this course
        students = await self.get_course_students(session, course['course_url'])
        
        # Save to database (synchronous operation)
        self.save_course(course, students)
        
        return len(students)
    
    async def scrape_all(self):
        """Main method to scrape all courses and students"""
        logger.info("Starting course scraping...")
        start_time = time.time()
        
        # Create SSL context that doesn't verify certificates
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Create aiohttp session with SSL context
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        async with aiohttp.ClientSession(connector=connector) as session:
            # Get list of all courses
            courses = await self.get_course_list(session)
            
            if not courses:
                logger.warning("No courses found. Please check the website structure.")
                return
            
            # Process all courses in parallel (limited by semaphore)
            tasks = [
                self.process_course(session, course, i+1, len(courses))
                for i, course in enumerate(courses)
            ]
            
            # Gather all results
            student_counts = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count total students (filter out exceptions)
            total_students = sum(count for count in student_counts if isinstance(count, int))
        
        elapsed_time = time.time() - start_time
        logger.info(f"Scraping completed in {elapsed_time:.2f} seconds")
        logger.info(f"Total courses: {len(courses)}")
        logger.info(f"Total students: {total_students}")
        logger.info(f"Database: {self.db_name}")
    
    def print_stats(self):
        """Print database statistics"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM courses')
        course_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM students')
        student_count = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT course_id, course_name, COUNT(*) as student_count
            FROM students
            JOIN courses USING(course_id)
            GROUP BY course_id
            ORDER BY student_count DESC
            LIMIT 5
        ''')
        top_courses = cursor.fetchall()
        
        conn.close()
        
        print("\n" + "="*60)
        print("DATABASE STATISTICS")
        print("="*60)
        print(f"Total courses: {course_count}")
        print(f"Total students: {student_count}")
        print("\nTop 5 courses by enrollment:")
        for course_id, course_name, count in top_courses:
            print(f"  {course_id}: {course_name} ({count} students)")
        print("="*60 + "\n")


async def main():
    """Main entry point"""
    scraper = CourseScraper()
    
    try:
        await scraper.scrape_all()
        scraper.print_stats()
    except KeyboardInterrupt:
        logger.info("\nScraping interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(main())
