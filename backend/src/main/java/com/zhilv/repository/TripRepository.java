package com.zhilv.repository;

import com.zhilv.entity.Trip;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface TripRepository extends JpaRepository<Trip, Long> {

    /** 按用户查历史行程,新的排前面(不分页) */
    List<Trip> findByUserIdOrderByCreatedAtDesc(Long userId);

    /** 按用户分页查历史行程,新的排前面 */
    Page<Trip> findByUserIdOrderByCreatedAtDesc(Long userId, Pageable pageable);
}
