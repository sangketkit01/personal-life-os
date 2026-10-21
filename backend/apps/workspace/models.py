import uuid
from django.db import models
from django.conf import settings


class TaskStatus(models.TextChoices):
    DRAFTING = 'DRAFTING', 'กำลังจัดทำ/เตรียมเอกสาร'
    WAITING = 'WAITING', 'รอส่ง/รอเซ็น/รอปลายทางตอบกลับ'
    COMPLETED = 'COMPLETED', 'เสร็จสิ้น/เรียบร้อย'
    ARCHIVED = 'ARCHIVED', 'เก็บเข้าคลังประวัติ'


class TaskPriority(models.TextChoices):
    LOW = 'LOW', 'ต่ำ'
    MEDIUM = 'MEDIUM', 'ปานกลาง'
    HIGH = 'HIGH', 'สูง'
    URGENT = 'URGENT', 'ด่วนที่สุด'


class WorkspaceProject(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='workspace_projects',
        verbose_name="เจ้าของโครงการ"
    )
    name = models.CharField(max_length=100, verbose_name="ชื่อกลุ่มงาน/โครงการ")
    description = models.TextField(blank=True, default='', verbose_name="คำอธิบาย")
    color = models.CharField(max_length=20, default='#3B82F6', verbose_name="สีประจำกลุ่ม (Hex)")
    icon = models.CharField(max_length=50, default='briefcase', verbose_name="ไอคอน (Lucide name)")
    is_archived = models.BooleanField(default=False, verbose_name="เก็บเข้ากรุแล้ว")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workspace_projects'
        ordering = ['name']
        verbose_name = 'กลุ่มงาน (Project)'
        verbose_name_plural = 'กลุ่มงานทั้งหมด'

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class TaskDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='task_documents',
        verbose_name="เจ้าของเอกสาร/งาน"
    )
    project = models.ForeignKey(
        WorkspaceProject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents',
        verbose_name="กลุ่มงาน"
    )
    title = models.CharField(max_length=255, verbose_name="ชื่องาน/ชื่อเอกสาร")
    doc_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="เลขที่เอกสาร (ถ้ามี)"
    )
    status = models.CharField(
        max_length=20,
        choices=TaskStatus.choices,
        default=TaskStatus.DRAFTING,
        db_index=True,
        verbose_name="สถานะเอกสาร"
    )
    priority = models.CharField(
        max_length=10,
        choices=TaskPriority.choices,
        default=TaskPriority.MEDIUM,
        verbose_name="ความสำคัญ"
    )
    deadline = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name="กำหนดส่ง (Deadline)"
    )
    file_url = models.TextField(
        blank=True,
        default='',
        verbose_name="ลิงก์เอกสาร / Google Drive"
    )
    notes = models.TextField(blank=True, default='', verbose_name="บันทึกรายละเอียด")
    metadata = models.JSONField(default=dict, blank=True, verbose_name="ข้อมูลเพิ่มเติม (JSONB)")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="เสร็จสิ้นเมื่อ")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'task_documents'
        ordering = ['deadline', '-created_at']
        verbose_name = 'งานและเอกสาร'
        verbose_name_plural = 'งานและเอกสารทั้งหมด'

    def __str__(self):
        return f"{self.title} [{self.get_status_display()}]"


class Note(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notes',
        verbose_name="เจ้าของโน้ต"
    )
    project = models.ForeignKey(
        WorkspaceProject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notes',
        verbose_name="กลุ่มงาน"
    )
    title = models.CharField(max_length=255, verbose_name="หัวข้อโน้ต")
    content = models.TextField(blank=True, default='', verbose_name="เนื้อหา Markdown")
    tags = models.JSONField(default=list, blank=True, verbose_name="แท็ก (Array of strings)")
    is_pinned = models.BooleanField(default=False, verbose_name="ปักหมุดไว้บนสุด")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'workspace_notes'
        ordering = ['-is_pinned', '-updated_at']
        verbose_name = 'โน้ต'
        verbose_name_plural = 'โน้ตทั้งหมด'

    def __str__(self):
        return self.title
